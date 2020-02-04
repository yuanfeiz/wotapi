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
    DetectorService,
)
from wotapi.socket_io import socket_io
from wotapi.utils import logger
from wotapi.views import routes
import os


def sanity_check(app):
    # Detector Service
    detector_service: DetectorService = app['detector_service']
    assert detector_service.connected()

    camera_service: CameraService = app['camera_service']
    assert camera_service.connected()


async def on_startup(app):
    sanity_check(app)

    camera_service: CameraService = app["camera_service"]
    await camera_service.init_subscribers()

    sensor_service: SensorService = app["sensor_service"]
    app["camera_feed"] = None
    app["results_path_feed"] = None

    async def start_feeds():
        await camera_service.emit_status_queue_item()

    async def sub_intensity_feed():
        async for item in camera_service.intensity_stream:
            await socket_io.emit("on_intensity_updated", item)

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
                sub_intensity_feed(),
                sub_sensor_reading_feed(),
                sub_results_path_feed(),
            },
            return_when=asyncio.FIRST_EXCEPTION,
        ))


# Setup CORS
def setup_cors(app):
    cors = aiohttp_cors.setup(
        app,
        defaults={
            "*":
            aiohttp_cors.ResourceOptions(allow_headers=("X-Requested-With",
                                                        "Content-Type")),
        },
    )
    for route in list(app.router.routes()):
        cors.add(route)


# Bind socket.io endpoints to the app
def setup_socket_io(app):
    socket_io.attach(app)


def setup_services(app, config):

    app["detector_service"] = DetectorService(config)

    path = Path(config.get("setting_service", "path"))
    app["setting_service"] = SettingService(path)

    path = Path(config.get("task_service", "path"))
    app["task_service"] = TaskService(path)

    # Inject task_service and setting_service into the CameraService
    app["camera_service"] = CameraService(
        app["task_service"],
        app["setting_service"],
        app["detector_service"],
        config,
    )

    app["auto_service"] = AutoService(config, app["task_service"],
                                      app["camera_service"])
    app["machine_service"] = MachineService(app["task_service"],
                                            app["setting_service"])

    path = config.get("sensor_service", "PATH")
    app["sensor_service"] = SensorService(path, sampling_freq=0.5)

    return app


def setup_app(app, config):
    # Setup routers
    app = setup_services(app, config)

    app.add_routes(routes)
    app.add_routes([web.static("/assets", "./assets", show_index=True)])

    if not os.getenv('GITHUB_ACTIONS'):
        # not to add static files during CI
        app.add_routes(
            [web.static("/app", "../wotapp/dist/", show_index=True)])
    app.on_startup.append(on_startup)

    setup_cors(app)
    setup_socket_io(app)

    return app
