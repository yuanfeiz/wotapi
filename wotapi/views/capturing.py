from wotapi.models import TaskState
from aiohttp import web
from ..services import TaskService, MachineService, CameraService
from ..utils import logger, id_factory
import asyncio
from .socket_helpers import notify_done, notify_updated
from .helpers import json_response
import time

routes = web.RouteTableDef()


async def _operate_machine(request: web.Request, coro) -> web.Response:
    task_service: TaskService = request.app["task_service"]
    started_at = time.time()

    tid = await coro
    try:
        logger.debug("Waiting for task to finish")
        await task_service.running_tasks[tid]

        return json_response({
            "id": tid,
            "state": TaskState.Completed,
            "startedAt": started_at
        })
    except Exception as e:
        return json_response(
            {
                "id": tid,
                'state': TaskState.Failed,
                'startedAt': started_at,
                'endedAt': time.time()
            },
            status=500)


@routes.post("/tasks/capturing/laser")
async def start_laser(request):
    machine_service: MachineService = request.app["machine_service"]
    return await _operate_machine(request, machine_service.start_laser())


@routes.post("/tasks/capturing/pzt")
async def start_cpzt(request):
    machine_service: MachineService = request.app["machine_service"]
    return await _operate_machine(request, machine_service.start_pzt())


@routes.post("/tasks/capturing/syringe_pump")
async def control_syringe_pump(request):
    machine_service: MachineService = request.app["machine_service"]
    action = (await request.json())["value"]
    assert action in ["infuse", "withdraw", "stop"], f"{action=} is invalid"

    return await _operate_machine(request,
                                  machine_service.control_syringe_pump(action))


@routes.post("/tasks/capturing/reset_particle_count")
async def reset_particle_count(request):
    camera_service: CameraService = request.app["camera_service"]
    await camera_service.reset_particle_count()
    tid = id_factory.get()
    return json_response({"id": tid, "status": "done"})


@routes.post("/tasks/capturing/capturing")
async def submit_capturing_task(request):
    camera_service: CameraService = request.app["camera_service"]
    task_service: TaskService = request.app["task_service"]
    tid, queue = await camera_service.start_manual_capturing()
    t = task_service.get(tid)
    asyncio.create_task(notify_done(t))
    return json_response({"id": tid})


@routes.post(r"/tasks/capturing/{action}")
async def submit_clean_task(request):
    machine_service: MachineService = request.app["machine_service"]
    task_service: TaskService = request.app["task_service"]
    action = request.match_info["action"]
    assert action in ["chipclean_surf", "chipclean_bleach", "chipclean_bs"]
    tid, _ = await machine_service.clean(action)
    t = task_service.get(tid)

    asyncio.create_task(notify_done(t))

    return json_response({"id": tid})