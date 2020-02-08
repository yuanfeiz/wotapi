import asyncio
import time
from wotapi.models import TaskState

from aiohttp import web

from ..services import AutoService, TaskService
from ..utils import logger
from .log_parser import RunProgressParser, SchedulerEventParser
from .socket_helpers import notify_done, notify_updated
from ..libs.json_helpers import json_response

routes = web.RouteTableDef()


@routes.post("/tasks/auto/{mode}")
async def start_auto_mode_task(request):
    data = await request.json()
    mode = request.match_info["mode"]

    auto_service: AutoService = request.app["auto_service"]
    task_service: TaskService = request.app["task_service"]

    tid, scheduler_sub, worker_sub = await auto_service.schedule(mode, **data)

    t = task_service.running_tasks[tid]
    logger.debug(f"Subscribe to task({mode}/{tid}) updates")

    asyncio.create_task(
        # Cancel progress report when task is done(reflecting by t)
        asyncio.wait({
            notify_done(t),
            notify_updated(tid, scheduler_sub, SchedulerEventParser()),
            notify_updated(tid, worker_sub, RunProgressParser()),
        }))

    return json_response({
        "id": tid,
        "state": TaskState.Queued.value,
        'mode': mode,
        'options': data,
        "startedAt": time.time()
    })


@routes.get("/auto/results")
async def get_all_results(request):
    """
    Historical data

    It's called on AutoMode page loaded as well as 
    on `onAutoModeDataUpdated` emitted
    """
    auto_service: AutoService = request.app["auto_service"]
    ret = await auto_service.get_all_results()
    return json_response({'results': ret})


@routes.get('/auto/results/{date}')
async def get_result_by_date(request):
    auto_service: AutoService = request.app["auto_service"]
    date = request.match_info['date']
    ret = await auto_service.get_results_by_date(date)
    return json_response({'results': ret})
