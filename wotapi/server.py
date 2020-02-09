import asyncio
from multiprocessing import Value
from pathlib import Path
from wotapi.services.detection_results import DetectionResultsService

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
from wotapi.views import all_routes
import os
from aiojobs.aiohttp import setup as setup_aiojobs, get_scheduler_from_app
from wotapi.socket_views import (pub_squeue_items, sub_intensity_feed,
                                 sub_results_path_feed,
                                 sub_sensor_reading_feed)


async def sanity_check(app):
    # Detector Service
    detector_service: DetectorService = app['detector_service']
    assert detector_service.connected()

    camera_service: CameraService = app['camera_service']
    assert camera_service.connected()


async def setup_feeds(app):
    scheduler = get_scheduler_from_app(app)
    await scheduler.spawn(pub_squeue_items(app))
    await scheduler.spawn(sub_intensity_feed(app))
    await scheduler.spawn(sub_results_path_feed(app))
    await scheduler.spawn(sub_sensor_reading_feed(app))

    return app


async def on_startup(app):
    await sanity_check(app)
    await setup_feeds(app)


async def on_cleanup(app):
    logger.info('clean up app')
    scheduler = get_scheduler_from_app(app)
    logger.info(f'closing scheduler: {scheduler}')
    await scheduler.close()


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

    app["detection_results_service"] = DetectionResultsService(config)

    path = config.get("sensor_service", "PATH")
    app["sensor_service"] = SensorService(path, sampling_freq=0.5)

    return app


def setup_app(app, config):
    # Setup routers
    app = setup_services(app, config)

    app.add_routes(all_routes)
    app.add_routes([web.static("/assets", "./assets", show_index=True)])

    # not to add static files during CI
    if not os.getenv('GITHUB_ACTIONS'):
        app.add_routes(
            [web.static("/app", "../wotapp/dist/", show_index=True)])

    setup_aiojobs(app)
    setup_cors(app)
    setup_socket_io(app)

    # run after setup_aiojobs
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    return app
