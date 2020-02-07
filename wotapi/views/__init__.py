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
from .images import routes as images_routes
from .capturing import routes as capturing_routes
from .detection import routes as detection_routes
from .helpers import json_response

routes = web.RouteTableDef()


@routes.get("/status")
async def status(request):
    return json_response({"status": "ok"})


@routes.delete(r"/capturing/tasks/capturing/{tid}")
async def cancel_capturing_task(request):
    tid = request.match_info.get("tid")
    camera_service: CameraService = request.app["camera_service"]
    exit_code = await camera_service.stop_capturing(tid)
    return json_response({"status": "ok", "id": tid, "exit_code": exit_code})


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
        return json_response({
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
    return json_response({"id": tid, "cancelled": cancelled})


all_routes = [
    *routes, *settings_routes, *automode_routes, *concentration_routes,
    *images_routes, *capturing_routes, *detection_routes
]
