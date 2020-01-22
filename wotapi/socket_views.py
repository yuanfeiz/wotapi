"""
Socket IO endpoints
"""
from wotapi.utils import logger
from wotapi.socket_io import socket_io


@socket_io.on("message")
async def get_message(id, message):
    logger.debug(f"socketio: get message message={message}, id={id}")
    for s in message:
        await socket_io.emit("message", f"you said {s}")


@socket_io.on("connect")
async def foo(sid, data):
    logger.debug(f"Client connected: {sid}")
