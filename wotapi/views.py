"""
HTTP endpoints
"""
import asyncio
import datetime

from aiohttp import web

from wotapi.services import AutoService, DetectorService
from wotapi.services.autoflow_parser import AutoflowParser
from wotapi.utils import logger
from wotapi.socket_io import socket_io
from wotapi.utils import id_factory
import paco

from configparser import ConfigParser

config = ConfigParser()
config.read_dict(
    {
        "auto": {
            "start_auto_mode_script_path": "/home/yuanfei/projects/siu/wot-core/mocks/startautoflow.py"
            # "tests/resources/mock_auto_mode.py"
        }
    }
)

routes = web.RouteTableDef()

# TODO: inject these dependencies
auto_service = AutoService(config)
detection_service = DetectorService()

__all__ = ["routes"]


@routes.get("/status")
async def status(request):
    return web.json_response({"status": "ok"})


@routes.get("/auto/results")
async def get_auto_mode_results(request):
    """
    Get historical and today's data for AutoMode.

    It's called on AutoMode page loaded as well as on `onAutoModeDataUpdated` emitted
    """
    now = datetime.datetime.now()
    ret = await auto_service.get_results()
    return web.json_response(ret)


@routes.post("/auto/tasks")
async def start_auto_mode_task(request):
    data = await request.json()
    mode = data["mode"]

    # Scheduled task id
    tid = None
    t: asyncio.Task = None
    progress: asyncio.Queue = asyncio.Queue()

    if mode == "single":
        tid, t, progress = await auto_service.schedule_run_once()
    elif mode == "period":
        tid, t, progress = await auto_service.schedule_run_period()
    elif mode == "scheduled":
        times = data["times"]
        tid, t, progress = await auto_service.schedule_run_multiple(times)

    async def notify_done(t):
        ret = await t
        logger.debug(f"task {tid} completed: {ret}")
        await socket_io.emit("on_auto_mode_task_done", ret)

    async def notify_updated(q: asyncio.Queue):
        parser = AutoflowParser()
        try:
            while True:
                s = await q.get()
                ret = parser.parse(s)
                logger.debug(f"Task {tid} gets new update: {ret}")
                if ret is not None and ret["event"] == "progress":
                    await socket_io.emit("on_auto_mode_task_updated", ret["progress"])
        except asyncio.CancelledError:
            logger.debug(f"progress for {tid} is canceled")

    logger.debug(f"Subscribe to task({mode}/{tid}) updates: {progress}")
    asyncio.create_task(
        # Cancel progress report when task is done(reflecting by t)
        paco.race([notify_done(t), notify_updated(progress)])
    )

    return web.json_response({"status": "ok", "id": tid})


@routes.delete(r"/auto/tasks/{tid:\w+}")
async def stop_auto_mode_task(request):
    tid = request.match_info.get("tid")
    auto_service.cancel_running_task(tid)
    return web.json_response({"status": "ok", "tid": tid})


@routes.post("/detection/tasks")
async def start_detection(request):
    json = await request.json()
    rid = id_factory.generate()

    # Emit progress pct to UI
    async def emit_progress_events():
        async for pct in detection_service.get_progress_events():
            await socket_io.emit("detection_progress_event", {"rid": rid, "pct": pct})

    socket_io.start_background_task(emit_progress_events)

    return web.json_response({"status": "ok", "rid": rid, "request_body": json})


@routes.delete(r"/detection/tasks/{tid:\w+}")
async def stop_detection(request):
    tid = request.match_info.get("tid")
    return web.json_response({"status": "ok", "tid": tid})
