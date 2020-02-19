from typing import Awaitable, Coroutine, Union
from wotapi.models import TaskState
from aiohttp import web
from ..services import TaskService, MachineService, CameraService
from ..utils import logger, id_factory, now
import asyncio
from .socket_helpers import notify_done, notify_updated
from ..libs.json_helpers import json_response
import time

routes = web.RouteTableDef()


async def spawn_and_respond(
        request: web.Request, coro: Union[asyncio.Task,
                                          Awaitable[str]]) -> web.Response:
    task_service: TaskService = request.app["task_service"]

    if isinstance(coro, asyncio.Task):
        t: asyncio.Task = coro
        tid = t.get_name()
    else:
        tid = await coro
        t = task_service.get(tid)

    asyncio.create_task(notify_done(t))

    return json_response({
        "id": tid,
        "state": TaskState.Ongoing,
        "startedAt": now()
    })


@routes.post("/tasks/capturing/laser")
async def start_laser(request):
    machine_service: MachineService = request.app["machine_service"]
    return await spawn_and_respond(request, machine_service.start_laser())


@routes.post("/tasks/capturing/pzt")
async def start_cpzt(request):
    machine_service: MachineService = request.app["machine_service"]
    return await spawn_and_respond(request, machine_service.start_pzt())


@routes.post('/tasks/capturing/mfs_pump')
async def start_mfs_pump(request):
    task_service: TaskService = request.app["task_service"]
    machine_service: MachineService = request.app["machine_service"]
    payload = (await request.json())

    action = payload["mode"]

    t = task_service.create_task(machine_service.control_mfs_pump(action))

    return await spawn_and_respond(request, t)


@routes.post("/tasks/capturing/syringe_pump")
async def control_syringe_pump(request):
    machine_service: MachineService = request.app["machine_service"]
    task_service: TaskService = request.app["task_service"]

    payload = await request.json()
    action = payload["mode"]

    assert action in ["infuse", "withdraw", "stop"], f"{action=} is invalid"

    t = task_service.create_task(machine_service.control_syringe_pump(action))

    return await spawn_and_respond(request, t)


@routes.post("/tasks/capturing/reset_particle_count")
async def reset_particle_count(request):
    camera_service: CameraService = request.app["camera_service"]
    t = asyncio.create_task(camera_service.reset_particle_count())
    asyncio.create_task(notify_done(t))
    return json_response({"id": t.get_name(), "state": TaskState.Ongoing})


@routes.post(r"/tasks/capturing/{action}")
async def submit_main_task(request):
    machine_service: MachineService = request.app["machine_service"]
    camera_service: CameraService = request.app["camera_service"]
    task_service: TaskService = request.app["task_service"]

    action = request.match_info["action"]

    # check action is vaid
    group, script_name = action.split('.')
    assert group == 'main'

    # machine service handles script name parsing
    if script_name in ["chipclean_surf", "chipclean_bleach", "mfs_otc"]:
        return await spawn_and_respond(request,
                                       task_service.create_script_task(action))
    elif script_name == 'capturing':
        return await spawn_and_respond(
            request,
            task_service.create_task(camera_service.start_manual_capturing()))
    else:
        raise Exception(f'invalid action name: {action}')