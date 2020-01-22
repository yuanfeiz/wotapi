"""
HTTP endpoints
"""
import asyncio
import datetime

from aiohttp import web

from wotapi.services import AutoService, DetectorService
from wotapi.utils import logger
from wotapi.socket_io import socket_io
from wotapi.utils import id_factory

routes = web.RouteTableDef()

# TODO: inject these dependencies
auto_service = AutoService()
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

    if mode == "single":
        tid, t = await auto_service.schedule_run_once()
    elif mode == "period":
        tid, t = await auto_service.schedule_run_period()
    elif mode == "scheduled":
        times = data["times"]
        tid, t = await auto_service.schedule_run_multiple(times)

    async def notify_auto_mode_task_done(t):
        ret = await t
        logger.debug(f"task {tid} completed: {ret}")
        await socket_io.emit("on_auto_mode_data_updated", ret)

    logger.debug("created task for emit auto_mode done result")
    asyncio.create_task(notify_auto_mode_task_done(t))

    return web.json_response({"status": "ok", "id": tid})


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


@routes.delete("/detection/tasks")
async def stop_detection(request):
    json = await request.json()
    return web.json_response({"status": "ok", "rid": json["rid"]})

