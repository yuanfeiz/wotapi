from aiohttp import web
from ..utils import id_factory
from ..socket_io import socket_io
from ..services import DetectorService

routes = web.RouteTableDef()


@routes.post("/detection/tasks")
async def start_detection(request):
    json = await request.json()
    rid = id_factory.get()
    detection_service: DetectorService = request.app["detection_service"]

    # Emit progress pct to UI
    async def emit_progress_events():
        async for pct in detection_service.get_progress_events():
            await socket_io.emit("detection_progress_event", {
                "rid": rid,
                "pct": pct
            })

    socket_io.start_background_task(emit_progress_events)

    return web.json_response({
        "status": "ok",
        "rid": rid,
        "request_body": json
    })


@routes.delete(r"/detection/tasks/{tid:\w+}")
async def stop_detection(request):
    tid = request.match_info.get("tid")
    return web.json_response({"status": "ok", "tid": tid})