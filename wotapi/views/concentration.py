from wotapi.services.task import TaskService
from wotapi.services.machine import MachineService
from aiohttp import web
from .socket_helpers import spawn_and_respond

routes = web.RouteTableDef()


@routes.post("/tasks/concentration/{action}")
async def submit_concentration_task(request):
    machine_service: MachineService = request.app['machine_service']
    task_service: TaskService = request.app['task_service']
    action = request.match_info.get('action')
    t = task_service.create_task(
        machine_service.run_concentration_task(action))
    return await spawn_and_respond(request, t)
