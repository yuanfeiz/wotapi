from configparser import ConfigParser
from unittest.mock import AsyncMock, MagicMock, Mock, call
from aiohttp import web
from wotapi.server import setup_app


async def test_get_status(aiohttp_client, mocker):
    m: Mock = mocker.patch('wotapi.server.sanity_check')
    app = setup_app(web.Application(), MagicMock(ConfigParser))
    cli = await aiohttp_client(app)
    resp = await cli.get("/status")

    assert await resp.json() == {"status": "ok"}
    m.assert_called_once_with(app)


async def test_patch_coro_py38(mocker):
    class Foo:
        async def foo(self, n):
            return n * n

    f = Foo()
    m: AsyncMock = mocker.patch.object(f, 'foo', return_value=1)
    assert await f.foo(20) == 1
    m.assert_awaited_once()
