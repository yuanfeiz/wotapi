"""
HTTP endpoints
"""
import asyncio
import time
from aiohttp import web

from aio_pubsub.interfaces import Subscriber

from wotapi.services import (
    AutoService,
    DetectorService,
    SettingService,
    TaskService,
    TaskDone,
    CameraService,
    MachineService,
)
from wotapi.services.log_parser import (
    LogParser,
    RunProgressParser,
    SchedulerEventParser,
)
from wotapi.services import image
from wotapi.utils import logger
from wotapi.socket_io import socket_io
from wotapi.utils import id_factory
import paco
from aiohttp import MultipartWriter

routes = web.RouteTableDef()


async def _on_progress(tid, queue: asyncio.Queue):
    while True:
        item = await queue.get()
        queue.task_done()
        logger.debug(f"Get task({tid}) progress item: {item}")
        if item == TaskDone:
            await socket_io.emit("task_done", {"id": tid})
            return
        elif isinstance(item, asyncio.CancelledError):
            # Terminate the queue if task is abort.
            await socket_io.emit("task_abort", {"id": tid, "msg": str(item)})
            return
        else:
            await socket_io.emit("task_updated", {"id": tid, "msg": item})
    logger.debug(f"Stop listen to _on_progress messages")


@routes.get("/status")
async def status(request):
    return web.json_response({"status": "ok"})


@routes.get("/auto/results")
async def get_auto_mode_results(request):
    """
    Get historical and today's data for AutoMode.

    It's called on AutoMode page loaded as well as 
    on `onAutoModeDataUpdated` emitted
    """
    auto_service: AutoService = request.app["auto_service"]
    ret = await auto_service.get_results()
    return web.json_response(ret)


async def notify_done(t: asyncio.Task):
    """
    Applicable for single mode only
    """
    tid = t.get_name()
    try:
        ret = await t
        logger.debug(f"task {tid} completed: {ret}")
        await socket_io.emit(
            "task_state",
            {
                "id": tid,
                "state": "k_completed",
                "endedAt": int(time.time()),
            },
        )
    except Exception as e:
        logger.exception(f"task {tid} failed: {e}")
        await socket_io.emit(
            "task_state",
            {
                "id": tid,
                "state": "k_failed",
                "endedAt": int(time.time()),
                "msg": str(e),
            },
        )


async def notify_updated(tid: str, sub: Subscriber, parser: LogParser):
    try:
        async for s in sub:
            ret = parser.parse(s)
            logger.info(f"Task {tid} gets new update: {ret}")
            if ret is not None and ret["event"] == "progress":
                await socket_io.emit("task_logs", ret["progress"])
    except asyncio.CancelledError:
        logger.debug(f"progress for {tid} is canceled")


@routes.post("/tasks/auto/{mode}")
async def start_auto_mode_task(request):
    data = await request.json()
    mode = request.match_info["mode"]

    auto_service: AutoService = request.app["auto_service"]
    task_service: TaskService = request.app["task_service"]

    if mode in ["single", "period"]:
        tid, scheduler_sub, worker_sub = await auto_service.schedule(mode)
    elif mode == "scheduled":
        times = data["times"]
        tid, scheduler_sub, worker_sub = await auto_service.schedule(
            mode, times=times)

    t = task_service.running_tasks[tid]

    logger.debug(f"Subscribe to task({mode}/{tid}) updates")

    asyncio.create_task(
        # Cancel progress report when task is done(reflecting by t)
        paco.race([
            notify_done(t),
            notify_updated(tid, scheduler_sub, SchedulerEventParser()),
            notify_updated(tid, worker_sub, RunProgressParser()),
        ]))

    return web.json_response({
        "state": "k_queued",
        "id": tid,
        "startedAt": time.time()
    })


@routes.post("/detection/tasks")
async def start_detection(request):
    json = await request.json()
    rid = id_factory.generate()
    detection_service: DetectorService = request.app["detection_service"]

    # Emit progress pct to UI
    async def emit_progress_events():
        async for pct in detection_service.get_progress_events():
            await socket_io.emit("detection_progress_event", {
                "rid": rid,
                "pct": pct
            })

    socket_io.start_background_task(emit_progress_events)

    return web.json_response({
        "status": "ok",
        "rid": rid,
        "request_body": json
    })


@routes.delete(r"/detection/tasks/{tid:\w+}")
async def stop_detection(request):
    tid = request.match_info.get("tid")
    return web.json_response({"status": "ok", "tid": tid})


@routes.get("/settings")
async def get_settings(request):
    setting_service: SettingService = request.app["setting_service"]
    return web.json_response({
        "settings": await setting_service.get(),
        "meta": {
            "path": str(setting_service.path)
        },
    })


@routes.put("/settings")
async def update_settings(request):
    payload = await request.json()
    new_settings = payload["settings"]

    # the update key can be none for mirror changes that
    # doesn't have side effect
    updated_key = payload.get("key")

    # Update the config file
    setting_service: SettingService = request.app["setting_service"]
    await setting_service.update(new_settings)

    camera_service: CameraService = request.app["camera_service"]
    if updated_key == "ITH":
        # Request detector to update its parameters
        params = new_settings["ITH"]
        await camera_service.update_intensity_levels(*params)
    elif updated_key == "CAMERA.EXP":
        new_value = new_settings["CAMERA"]["EXP"][1]
        await camera_service.update_camera_exp(new_value)
    elif updated_key == "CAMERA.GAIN":
        new_value = new_settings["CAMERA"]["GAIN"][1]
        await camera_service.update_camera_gain(new_value)

    return web.json_response({"status": "ok", "settings": new_settings})


@routes.post("/concentration/tasks")
async def submit_concentration_task(request):
    payload = await request.json()
    action = payload["action"]
    task_service: TaskService = request.app["task_service"]
    queue = asyncio.Queue()

    tid = await task_service.submit(action, queue)

    t = asyncio.create_task(_on_progress(tid, queue))

    return web.json_response({"id": tid})


@routes.delete(r"/concentration/tasks/{tid}")
async def cancel_concentration_task(request):
    tid = request.match_info.get("tid")
    task_service: TaskService = request.app["task_service"]
    try:
        await task_service.cancel(tid)
        return web.json_response({"status": "ok"})
    except Exception as e:
        return web.json_response({
            "status": "error",
            "msg": str(e)
        },
                                 status=500)


async def write_new_parts(data, boundary, response):
    with MultipartWriter("image/jpeg", boundary=boundary) as mpwriter:

        mpwriter.append(data, {"Content-Type": "image/jpeg"})
        # mpwriter.append(byte_im, {"Content-Type": "image/jpeg"})
        await mpwriter.write(response, close_boundary=False)
        logger.debug(f"Append response")
    await response.drain()


@routes.get(r"/capturing/feeds/{img_type}")
async def timg_feed(request) -> web.StreamResponse:
    my_boundary = "some-boundary"

    response = web.StreamResponse(
        status=200,
        reason="OK",
        headers={
            "Content-Type":
            "multipart/x-mixed-replace;boundary=--%s" % my_boundary
        },
    )
    await response.prepare(request)

    csrv: CameraService = request.app["camera_service"]
    img_stream = await csrv.hub.subscribe("image")
    img_type = request.match_info.get("img_type").upper()
    logger.debug(f"Subscribe to image stream {img_type=}")

    await write_new_parts(image.img_to_bytes(image.blank_image()), my_boundary,
                          response)

    try:
        async for item in img_stream:
            if img_type not in item:
                logger.debug(f"Skip image item: {img_type=} {item.keys()}")
                continue

            img = image.frombuffer(item[img_type])
            await write_new_parts(image.img_to_bytes(img), my_boundary,
                                  response)
    except ConnectionResetError:
        logger.debug(f"Ignored premature client disconnection")

    logger.debug("Finished streaming")

    return response


@routes.delete(r"/capturing/tasks/capturing/{tid}")
async def cancel_capturing_task(request):
    tid = request.match_info.get("tid")
    camera_service: CameraService = request.app["camera_service"]
    exit_code = await camera_service.stop_capturing(tid)
    return web.json_response({
        "status": "ok",
        "id": tid,
        "exit_code": exit_code
    })


async def _operate_machine(request: web.Request, coro) -> web.Response:
    task_service: TaskService = request.app["task_service"]

    tid = await coro

    logger.debug("Waiting for task to finish")
    await task_service.running_tasks[tid]

    return web.json_response({"id": tid, "status": "done"})


@routes.post("/capturing/tasks/laser")
async def start_laser(request):
    machine_service: MachineService = request.app["machine_service"]
    return await _operate_machine(request, machine_service.start_laser())


@routes.post("/capturing/tasks/pzt")
async def start_cpzt(request):
    machine_service: MachineService = request.app["machine_service"]
    return await _operate_machine(request, machine_service.start_pzt())


@routes.post("/capturing/tasks/syringe_pump")
async def control_syringe_pump(request):
    machine_service: MachineService = request.app["machine_service"]
    action = (await request.json())["action"]
    assert action in ["infuse", "withdraw", "stop"], f"{action=} is invalid"

    return await _operate_machine(request,
                                  machine_service.control_syringe_pump(action))


@routes.post("/capturing/tasks/reset_particle_count")
async def reset_particle_count(request):
    camera_service: CameraService = request.app["camera_service"]
    await camera_service.reset_particle_count()
    tid = id_factory.get()
    return web.json_response({"id": tid, "status": "done"})


@routes.post("/capturing/tasks/capturing")
async def submit_capturing_task(request):
    camera_service: CameraService = request.app["camera_service"]
    tid, queue = await camera_service.start_manual_capturing()
    task = asyncio.create_task(_on_progress(tid, queue),
                               name="start_capturing")
    logger.debug(f"Created {task=}")
    return web.json_response({"id": tid})


@routes.post(r"/capturing/tasks/{action}")
async def submit_clean_task(request):
    machine_service: MachineService = request.app["machine_service"]
    action = request.match_info["action"]
    assert action in ["chipclean_surf", "chipclean_bleach", "chipclean_bs"]
    tid, queue = await machine_service.clean(action)
    task = asyncio.create_task(_on_progress(tid, queue), name=action)
    logger.debug(f"Created {task=}")
    return web.json_response({"id": tid})


async def publish_task_cancel_update(task: asyncio.Task):
    tid = task.get_name()
    try:
        # wait for the task to finish clean up
        await task
        # succeed cancelling the task
        await socket_io.emit("k_task_state", {
            "id": tid,
            "state": "k_cancelled"
        })
    except Exception as e:
        # cancellation went wrong..
        await socket_io.emit(
            "k_task_state",
            {
                "id": tid,
                "state": "k_cancel_failed",
                "msg": str(e)
            },
        )


@routes.delete(r"/tasks/{tid}")
async def cancel_task(request):
    tid = request.match_info.get("tid")
    task_service: TaskService = request.app["task_service"]
    try:
        task = task_service.running_tasks[tid]
    except KeyError:
        return web.json_response({
            "id": tid,
            "error": "task not found"
        },
                                 status=500)

    # Task might not be cancelled at this moment as cleanup will be invoked
    # inside the try/except blocks
    cancelled = task.cancel()
    if not cancelled:
        # waiting for clean ups
        # publish the state changes via socket
        asyncio.create_task(publish_task_cancel_update(task))

    # tell UI the progress of the cancellation
    return web.json_response({"id": tid, "cancelled": cancelled})
