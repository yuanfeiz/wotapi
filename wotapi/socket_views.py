"""
Socket IO endpoints
"""
from wotapi.services.sensor import SensorService
from wotapi.services.camera import CameraService
from wotapi.utils import logger
from wotapi.socket_io import socket_io
import asyncio


@socket_io.on("message")
async def get_message(id, message):
    logger.debug(f"socketio: get message message={message}, id={id}")
    for s in message:
        await socket_io.emit("message", f"you said {s}")


@socket_io.on("connect")
async def foo(sid, data):
    logger.debug(f"Client connected: {sid}")


async def pub_squeue_items(app):
    camera_service: CameraService = app["camera_service"]
    try:
        await camera_service.emit_status_queue_item()
    except asyncio.CancelledError as e:
        logger.info('stopped pub squeue items')
        raise e


async def sub_intensity_feed(app):
    logger.info('subscribed to intensity feeds')
    camera_service: CameraService = app["camera_service"]
    await camera_service.init_subscribers()
    try:
        async for item in camera_service.intensity_stream:
            await socket_io.emit("on_intensity_updated", item)
    except asyncio.CancelledError as e:
        logger.info('unsubscribe to intensity feed')
        raise e


async def sub_results_path_feed(app):
    logger.info('subscribed to results path feeds')
    camera_service: CameraService = app["camera_service"]
    feed = await camera_service.hub.subscribe("results_path")
    async for item in feed:
        logger.debug(item)
        await socket_io.emit("results_path", item)


async def sub_sensor_reading_feed(app):
    """
    This should be called for only once
    """
    logger.info('subscribed to sensor readings feeds')
    sensor_service: SensorService = app["sensor_service"]
    async for reading in sensor_service.on_reading():
        await socket_io.emit("on_sensor_reading", reading.to_json())