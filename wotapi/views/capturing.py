from wotapi.models import TaskState
from aiohttp import web
from ..services import TaskService, MachineService, CameraService
from ..utils import logger, id_factory, now
import asyncio
from .socket_helpers import notify_done, notify_updated
from ..libs.json_helpers import json_response
import time

routes = web.RouteTableDef()


async def _operate_machine(request: web.Request, coro) -> web.Response:
    task_service: TaskService = request.app["task_service"]

    tid = await coro

    asyncio.create_task(notify_done(task_service.get(tid)))

    return json_response({
        "id": tid,
        "state": TaskState.Ongoing,
        "startedAt": now()
    })


@routes.post("/tasks/capturing/laser")
async def start_laser(request):
    machine_service: MachineService = request.app["machine_service"]
    return await _operate_machine(request, machine_service.start_laser())


@routes.post("/tasks/capturing/pzt")
async def start_cpzt(request):
    machine_service: MachineService = request.app["machine_service"]
    return await _operate_machine(request, machine_service.start_pzt())


@routes.post('/tasks/capturing/mfs_pump')
async def start_mfs_pump(request):
    task_service: TaskService = request.app["task_service"]
    payload = (await request.json())

    return await _operate_machine(
        request,
        task_service.create_script_task(
            'mfspumpcontrol',
            None,
            kwargs={"__SINGLE": [payload['mode'], payload['args']]}))


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
    if script_name in ["chipclean_surf", "chipclean_bleach", "chipclean_bs"]:
        tid = await machine_service.clean(action)
    elif script_name == 'capturing':
        tid, _ = await camera_service.start_manual_capturing()
    else:
        raise Exception(f'invalid action name: {action}')

    t = task_service.get(tid)

    asyncio.create_task(notify_done(t))

    return json_response({
        "id": tid,
        'state': TaskState.Ongoing,
        'startedAt': now()
    })


@routes.delete(r"/capturing/tasks/capturing/{tid}")
async def cancel_capturing_task(request):
    tid = request.match_info.get("tid")
    camera_service: CameraService = request.app["camera_service"]
    exit_code = await camera_service.stop_capturing(tid)
    return json_response({"status": "ok", "id": tid, "exit_code": exit_code})