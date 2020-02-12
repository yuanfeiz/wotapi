from wotapi.views.socket_helpers import publish_task_cancel_update
from wotapi.libs.json_helpers import json_response
from wotapi.services.task import TaskService
from aiohttp import web
from ..models import TaskState

import asyncio
routes = web.RouteTableDef()


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
    return json_response({
        "id": tid,
        "state": TaskState.Cancelled,
        "cancelled": cancelled
    })
