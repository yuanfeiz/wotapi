import asyncio
from ..utils import logger
from ..socket_io import socket_io
from aio_pubsub.interfaces import Subscriber
import time
from .log_parser import LogParser


async def notify_done(t: asyncio.Task):
    """
    Applicable for single mode only
    """
    tid = t.get_name()
    try:
        ret = await t
        logger.info(f"task {tid} completed: {ret}")
        await socket_io.emit(
            "task_state",
            {
                "id": tid,
                "state": "k_completed",
                "endedAt": int(time.time()),
            },
        )
    except Exception as e:
        logger.exception(f"task {tid} failed: {e}")
        await socket_io.emit(
            "task_state",
            {
                "id": tid,
                "state": "k_failed",
                "endedAt": int(time.time()),
                "msg": str(e),
            },
        )


async def notify_updated(tid: str, sub: Subscriber, parser: LogParser):
    try:
        async for s in sub:
            ret = parser.parse(s)
            logger.info(f"Task {tid} gets new update: {ret}")
            await socket_io.emit("task_logs", ret)
    except asyncio.CancelledError:
        logger.debug(f"progress for {tid} is canceled")
    except Exception as e:
        logger.error(f'failed to emit task logs: {e}', debug=True)
