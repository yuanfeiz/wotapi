"""
HTTP endpoints
"""
import asyncio
import time

from multidict import MultiMapping
from wotapi.models import EventTopics, TaskState
from aiohttp import web

from wotapi.services import (
    TaskService,
    CameraService,
    MachineService,
)
from wotapi.services import image
from wotapi.utils import logger
from wotapi.socket_io import socket_io
from wotapi.utils import id_factory
from aiohttp import MultipartWriter
from .settings import routes as settings_routes
from .automode import routes as automode_routes
from .concentration import routes as concentration_routes

routes = web.RouteTableDef()


@routes.get("/status")
async def status(request):
    return web.json_response({"status": "ok"})


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
    return web.json_response({"id": tid})


@routes.post(r"/capturing/tasks/{action}")
async def submit_clean_task(request):
    machine_service: MachineService = request.app["machine_service"]
    action = request.match_info["action"]
    assert action in ["chipclean_surf", "chipclean_bleach", "chipclean_bs"]
    tid, queue = await machine_service.clean(action)
    return web.json_response({"id": tid})


async def publish_task_cancel_update(task: asyncio.Task):
    tid = task.get_name()
    try:
        # wait for the task to finish clean up
        await task
        # succeed cancelling the task
        await socket_io.emit(EventTopics.State, {
            "id": tid,
            "state": TaskState.Cancelled
        })
    except Exception as e:
        # cancellation went wrong..
        await socket_io.emit(
            EventTopics.State,
            {
                "id": tid,
                "state": TaskState.Failed,
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


all_routes = [
    *routes, *settings_routes, *automode_routes, *concentration_routes
]
