from wotapi.utils import logger
from wotapi.views.socket_helpers import notify_done
from aiohttp import web
import asyncio
from ..services import TaskService
from .socket_helpers import notify_done

routes = web.RouteTableDef()


@routes.post("/tasks/concentration/{action}")
async def submit_concentration_task(request):
    action = request.match_info.get('action')
    task_service: TaskService = request.app["task_service"]

    # submit script task
    tid = await task_service.submit(action)

    # emit task progress
    asyncio.create_task(notify_done(task_service.get(tid)))

    return web.json_response({"id": tid})