from typing import AsyncContextManager
from unittest.mock import AsyncMock, MagicMock, Mock, call
from wotapi.views.socket_helpers import notify_done, notify_updated
import pytest
import asyncio
import time
from aio_pubsub.interfaces import Subscriber


@pytest.mark.asyncio
async def test_notify_done_emit_on_ok(mocker):
    m: AsyncMock = mocker.patch('wotapi.socket_io.socket_io.emit')
    t = asyncio.create_task(asyncio.sleep(0, 'may'))
    await notify_done(t)
    m.assert_awaited_once()
    evt_name, evt = m.call_args.args
    assert evt_name == 'task_state'
    assert time.time() - evt['endedAt'] < 1
    assert evt['id'] == t.get_name()
    assert evt['state'] == 'k_completed'


@pytest.mark.asyncio
async def test_notify_done_emit_on_failed(mocker):
    m: AsyncMock = mocker.patch('wotapi.socket_io.socket_io.emit')

    async def error():
        raise Exception('foo')

    t = asyncio.create_task(error())
    await notify_done(t)
    m.assert_awaited_once()
    evt_name, evt = m.call_args.args
    assert evt_name == 'task_state'
    assert time.time() - evt['endedAt'] < 1
    assert evt['id'] == t.get_name()
    assert evt['state'] == 'k_failed'


@pytest.mark.asyncio
async def test_notify_update_emit_on_ok(mocker):
    m: AsyncMock = mocker.patch('wotapi.socket_io.socket_io.emit')

    async def sub_factory():
        for c in list('may'):
            yield c

    parser = MagicMock()
    parser.parse.side_effect = lambda x: x
    await notify_updated('foo', sub_factory(), parser)
    for ch, args in zip(list('may'), m.call_args_list):
        assert ('task_logs', ch) == args.args
