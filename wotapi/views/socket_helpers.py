import asyncio
from wotapi.services.task import TaskService
from wotapi.models import EventTopics, TaskState
from ..utils import logger
from ..socket_io import socket_io
from aio_pubsub.interfaces import Subscriber
import time
from .log_parser import LogParser


async def notify_done(t: asyncio.Task):
    tid = t.get_name()
    logger.debug(f'start task state notifier: {tid}')
    try:
        await socket_io.emit(EventTopics.State, {
            'id': tid,
            'state': TaskState.Ongoing,
            'startedAt': int(time.time()),
        })
        ret = await t
        logger.info(f"task {tid} completed: {ret}")
        await socket_io.emit(
            EventTopics.State,
            {
                "id": tid,
                "state": TaskState.Completed,
                "endedAt": int(time.time()),
            },
        )
    except asyncio.CancelledError:
        logger.warning(f'task {tid} cancelled')
        await socket_io.emit(
            EventTopics.State,
            {
                "id": tid,
                "state": TaskState.Cancelled,
                "endedAt": int(time.time()),
            },
        )
    except Exception as e:
        logger.exception(f"task {tid} failed: {e}")
        await socket_io.emit(
            EventTopics.State,
            {
                "id": tid,
                "state": TaskState.Failed,
                "endedAt": int(time.time()),
                "msg": str(e),
            },
        )
    finally:
        logger.debug(f'shutdown task state notifier: {tid}')


async def notify_updated(tid: str, sub: Subscriber, parser: LogParser):
    try:
        async for s in sub:
            ret = parser.parse(s)
            logger.info(
                f"Task {tid} gets new update: {ret=} original output: {s}")
            if ret is not None:
                await socket_io.emit("task_logs", ret)
    except asyncio.CancelledError:
        logger.debug(f"task log notifier for {tid} is canceled")
    except Exception as e:
        logger.error(f'failed to emit task logs: {e}')
    finally:
        logger.debug(f'shutdown task log notifier: {tid}')