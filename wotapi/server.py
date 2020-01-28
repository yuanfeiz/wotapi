from pathlib import Path

import aiohttp_cors
from aiohttp import web

from wotapi.services import (
    AutoService,
    DetectorService,
    SensorService,
    CameraService,
    SettingService,
    TaskService,
)
from wotapi.utils import logger
from wotapi.views import routes
from wotapi.socket_io import socket_io


async def on_startup(app):
    camera_service: CameraService = app["camera_service"]
    await camera_service.init_subscribers()

    sensor_service: SensorService = app["sensor_service"]

    async def bar():
        await camera_service.connect()

    async def wuz():
        async for item in camera_service.intensity_stream:
            await socket_io.emit("foo", item["stats"])

    async def monitor_cmd_queue():
        async for cmd in camera_service.get_cmd():
            logger.debug(f"got item from cmd queue: {cmd!s}")

    async def on_sensor_reading():
        """
        This should be called for only once
        """
        async for reading in sensor_service.on_reading():
            await socket_io.emit("on_sensor_reading", reading.to_json())

    socket_io.start_background_task(bar)
    socket_io.start_background_task(wuz)
    socket_io.start_background_task(on_sensor_reading)


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


def setup_services(app, config):
    app["auto_service"] = AutoService(config)

    path = Path(config.get("setting_service", "path"))
    app["setting_service"] = SettingService(path)

    app["camera_service"] = CameraService()

    path = Path(__file__).parent / ".." / "data" / "dfppmgui.json"
    path = str(path.resolve())
    app["sensor_service"] = SensorService(path, sampling_freq=0.5)


    path = Path(config.get('task_service', 'path'))
    app["task_service"] = TaskService(path)

    return app


def setup_app(app, config):
    # Setup routers
    app = setup_services(app, config)

    app.add_routes(routes)
    app.add_routes([web.static("/assets", "./assets", show_index=True)])
    # app.add_routes([web.static("/app", "./assets/app", show_index=True)])
    app.on_startup.append(on_startup)

    setup_cors(app)
    setup_socket_io(app)

    return app
