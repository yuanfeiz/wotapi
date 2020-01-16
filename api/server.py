from aiohttp import web
import socketio
import logging
import aiohttp_cors

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

socket_io = socketio.AsyncServer()


async def status(request):
    return web.json_response({"status": "ok"})


@socket_io.on("message")
async def get_message(id, message):
    logger.debug(f"socketio: get message {message=}, {id=}")
    await socket_io.emit("message", f"you said {message}")


if __name__ == "__main__":
    app = web.Application()

    # Setup routers
    app.add_routes([web.get("/status", status)])
    app.add_routes([web.static("/assets", "./assets", show_index=True)])

    # Setup CORS
    cors = aiohttp_cors.setup(
        app, defaults={"*": aiohttp_cors.ResourceOptions(),}
    )
    for route in list(app.router.routes()):
        cors.add(route)
    
    # Bind socket.io endpoints to the app
    socket_io.attach(app)

    # Kick off the game
    web.run_app(app)
