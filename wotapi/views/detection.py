from wotapi.views.log_parser import DetectionMuxLogParser
from wotapi.models import EventTopics, TaskState
from wotapi.services.task import TaskService
from ..utils import id_factory
from ..socket_io import socket_io
from ..services import DetectorService
from .socket_helpers import *
from .helpers import json_response
import paco
from aiohttp import web

routes = web.RouteTableDef()


@routes.post("/tasks/detection/start")
async def start_detection(request):
    payload = await request.json()
    path, monitor_mode = payload['path'], payload.get('monitorMode', False)

    detection_service: DetectorService = request.app["detector_service"]
    task_service: TaskService = request.app['task_service']
    t = task_service.create_task(detection_service.start(path, monitor_mode))
    tid = t.get_name()

    sub = await detection_service.hub.subscribe(EventTopics.Logs)
    mux_log_parser = DetectionMuxLogParser()

    asyncio.create_task(
        paco.race([notify_done(t),
                   notify_updated(tid, sub, mux_log_parser)]))

    return json_response({
        'id': tid,
        "state": TaskState.Queued.value,
    })
