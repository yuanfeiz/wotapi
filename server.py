from aiohttp import web
import socketio
import logging
import aiohttp_cors
import asyncio
from wotapi.services.camera import CameraService

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

socket_io = socketio.AsyncServer(logger=True, cors_allowed_origins="*")

cs = CameraService()


async def on_startup(app):
    await cs.init_subscribers()


async def status(request):
    return web.json_response({"status": "ok"})


@socket_io.on("message")
async def get_message(id, message):
    logger.debug(f"socketio: get message message={message}, id={id}")
    for s in message:
        await socket_io.emit("message", f"you said {s}")


@socket_io.on("connect")
async def foo(sid, data):
    logger.debug(f"calling foo")

    async def bar():
        await cs.connect()

    async def wuz():
        async for item in cs.intensity_stream:
            await socket_io.emit("foo", item['stats'])

    t1 = socket_io.start_background_task(bar)
    t2 = socket_io.start_background_task(wuz)


app = web.Application()

# Setup routers
app.add_routes([web.get("/status", status)])
app.add_routes([web.static("/assets", "./assets", show_index=True)])
app.on_startup.append(on_startup)

# Setup CORS
cors = aiohttp_cors.setup(app, defaults={"*": aiohttp_cors.ResourceOptions(),})
for route in list(app.router.routes()):
    cors.add(route)

# Bind socket.io endpoints to the app
socket_io.attach(app)

if __name__ == "__main__":

    # Kick off the game
    web.run_app(app)
