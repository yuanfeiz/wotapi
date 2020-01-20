from aiohttp import web
import socketio
import logging
import aiohttp_cors
import asyncio
from wotapi.services.camera import CameraService
from shortid import ShortId
from wotapi.services.detector import DetectorService
from wotapi.services.sensor import SensorService

sid = ShortId()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

socket_io = socketio.AsyncServer(logger=True, cors_allowed_origins="*")

cs = CameraService()
ds = DetectorService()

path = "/Users/yuanfei/Projects/siu/wot/wot-core/su/dfppmgui.json"
ss = SensorService(path, sampling_freq=0.5)


async def on_startup(app):
    await cs.init_subscribers()


async def status(request):
    return web.json_response({"status": "ok"})


async def start_detection(request):
    json = await request.json()
    rid = sid.generate()

    # Emit progress pct to UI
    async def emit_progress_events():
        async for pct in ds.get_progress_events():
            await socket_io.emit("detection_progress_event", {"rid": rid, "pct": pct})

    socket_io.start_background_task(emit_progress_events)

    return web.json_response({"status": "ok", "rid": rid, "request_body": json})


async def stop_detection(request):
    json = await request.json()
    return web.json_response({"status": "ok", "rid": json["rid"]})


@socket_io.on("message")
async def get_message(id, message):
    logger.debug(f"socketio: get message message={message}, id={id}")
    for s in message:
        await socket_io.emit("message", f"you said {s}")


async def on_sensor_reading():
    async for reading in ss.on_reading():
        await socket_io.emit("on_sensor_reading", reading.to_json())
        await asyncio.sleep(5)


@socket_io.on("connect")
async def foo(sid, data):
    logger.debug(f"calling foo")

    async def bar():
        await cs.connect()

    async def wuz():
        async for item in cs.intensity_stream:
            await socket_io.emit("foo", item["stats"])

    async def monitor_cmd_queue():
        async for cmd in cs.get_cmd():
            logger.debug(f"got item from cmd queue: {cmd!s}")

    t1 = socket_io.start_background_task(bar)
    t2 = socket_io.start_background_task(wuz)
    t3 = socket_io.start_background_task(on_sensor_reading)


app = web.Application()

# Setup routers
app.add_routes([web.get("/status", status)])
app.add_routes([web.post("/detection/start", start_detection)])
app.add_routes([web.post("/detection/stop", stop_detection)])
app.add_routes([web.static("/assets", "./assets", show_index=True)])
app.on_startup.append(on_startup)

# Setup CORS
cors = aiohttp_cors.setup(
    app,
    defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_headers=("X-Requested-With", "Content-Type")
        ),
    },
)
for route in list(app.router.routes()):
    cors.add(route)

# Bind socket.io endpoints to the app
socket_io.attach(app)

if __name__ == "__main__":

    # Kick off the game
    web.run_app(app, port=8082)
