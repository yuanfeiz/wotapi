import asyncio
from pathlib import Path

import aiohttp_cors
from aiohttp import web

from wotapi.services import (
    AutoService,
    CameraService,
    MachineService,
    SensorService,
    SettingService,
    TaskService,
)
from wotapi.socket_io import socket_io
from wotapi.utils import logger
from wotapi.views import routes


async def on_startup(app):
    camera_service: CameraService = app["camera_service"]
    await camera_service.init_subscribers()

    sensor_service: SensorService = app["sensor_service"]
    app["camera_feed"] = None
    app["results_path_feed"] = None

    async def start_feeds():
        await asyncio.gather(
            camera_service.emit_status_queue_item(),
            camera_service.emit_command_queue_item(),
        )

    async def sub_intensity_feed():
        async for item in camera_service.intensity_stream:
            a = item["samples"]
            await socket_io.emit("on_intensity_updated", item)

    async def sub_camera_info_feed():
        feed = await camera_service.hub.subscribe("camera_info")
        app["camera_feed"] = feed
        async for item in feed:
            logger.debug(item)

    async def sub_results_path_feed():
        feed = await camera_service.hub.subscribe("results_path")
        app["results_path_feed"] = feed
        async for item in feed:
            logger.debug(item)
            await socket_io.emit("results_path", item)

    async def sub_sensor_reading_feed():
        """
        This should be called for only once
        """
        async for reading in sensor_service.on_reading():
            await socket_io.emit("on_sensor_reading", reading.to_json())

    asyncio.create_task(start_feeds())
    asyncio.create_task(
        asyncio.wait(
            {
                sub_camera_info_feed(),
                sub_intensity_feed(),
                sub_sensor_reading_feed(),
                sub_results_path_feed(),
            },
            return_when=asyncio.FIRST_EXCEPTION,
        )
    )


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

    path = Path(config.get("task_service", "path"))
    app["task_service"] = TaskService(path)

    # Inject task_service and setting_service into the CameraService
    app["camera_service"] = CameraService(
        app["task_service"], app["setting_service"], config
    )

    app["machine_service"] = MachineService(
        app["task_service"], app["setting_service"]
    )

    path = config.get("sensor_service", "PATH")
    app["sensor_service"] = SensorService(path, sampling_freq=0.5)

    return app


def setup_app(app, config):
    # Setup routers
    app = setup_services(app, config)

    app.add_routes(routes)
    app.add_routes([web.static("/assets", "./assets", show_index=True)])
    app.add_routes([web.static("/app", "../wotapp/dist/", show_index=True)])
    app.on_startup.append(on_startup)

    setup_cors(app)
    setup_socket_io(app)

    return app
