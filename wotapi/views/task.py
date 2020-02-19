from ..utils import logger
from ..socket_io import socket_io
from wotapi.libs.json_helpers import json_response
from wotapi.services.task import TaskService
from aiohttp import web
from ..models import TaskState, EventTopics

import asyncio
routes = web.RouteTableDef()


@routes.delete(r"/tasks/{tid}")
async def cancel_task(request):
    tid = request.match_info.get("tid")
    task_service: TaskService = request.app["task_service"]

    # inform task is being cancelled
    await socket_io.emit(
        EventTopics.State,
        {
            "id": tid,
            "state": TaskState.Cancelling,
        },
    )

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
    task.cancel()
    task_service.clear(tid)

    # tell UI the progress of the cancellation
    return json_response({
        "id": tid,
        "state": TaskState.Cancelling,
    })
