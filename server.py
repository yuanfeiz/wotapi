import asyncio
import datetime
import logging
import time

import aiohttp_cors
from aiohttp import web

from wotapi.services import AutoService, DetectorService, SensorService, CameraService
from wotapi.utils import logger
from wotapi.views import routes
from wotapi.socket_io import socket_io


cs = CameraService()

path = "/Users/yuanfei/Projects/siu/wot/wot-core/su/dfppmgui.json"
ss = SensorService(path, sampling_freq=0.5)


async def on_startup(app):
    await cs.init_subscribers()

    async def bar():
        await cs.connect()

    async def wuz():
        async for item in cs.intensity_stream:
            await socket_io.emit("foo", item["stats"])

    async def monitor_cmd_queue():
        async for cmd in cs.get_cmd():
            logger.debug(f"got item from cmd queue: {cmd!s}")

    async def on_sensor_reading():
        """
        This should be called for only once
        """
        async for reading in ss.on_reading():
            await socket_io.emit("on_sensor_reading", reading.to_json())
            await asyncio.sleep(5)           

    t1 = socket_io.start_background_task(bar)
    t2 = socket_io.start_background_task(wuz)
    t3 = socket_io.start_background_task(on_sensor_reading)


# Setup CORS
def setup_cors(app):
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
def setup_socket_io(app):
    socket_io.attach(app)


def setup_app(app):
    # Setup routers
    app.add_routes(routes)
    app.add_routes([web.static("/assets", "./assets", show_index=True)])
    app.on_startup.append(on_startup)

    setup_cors(app)
    setup_socket_io(app)

    return app


app = web.Application()
setup_app(app)


if __name__ == "__main__":
    # Kick off the game
    web.run_app(app, port=8082)
