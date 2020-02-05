from wotapi.services.task import TaskService
from aiohttp import web
from ..utils import id_factory
from ..socket_io import socket_io
from ..services import DetectorService
from .socket_helpers import *
import paco

routes = web.RouteTableDef()


@routes.post("/detection/tasks")
async def start_detection(request):
    payload = await request.json()
    path, monitor_mode = payload['path'], payload.get('monitorMode', False)

    detection_service: DetectorService = request.app["detection_service"]
    task_service: TaskService = request.app['task_service']
    t = task_service.create_task(detection_service.start(path, monitor_mode))
    tid = t.get_name()
    sub = await task_service

    asyncio.create_task(paco.race([notify_done(t), notify_updated(tid, )]))

    return web.json_response({
        "status": "ok",
        "rid": rid,
        "request_body": json
    })


@routes.delete(r"/detection/tasks/{tid:\w+}")
async def stop_detection(request):
    tid = request.match_info.get("tid")
    return web.json_response({"status": "ok", "tid": tid})