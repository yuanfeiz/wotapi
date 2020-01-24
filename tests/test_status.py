import pytest
from aiohttp import web
from wotapi.server import setup_app


# @pytest.mark.asyncio
async def test_get_status(aiohttp_client):
    app = setup_app(web.Application())
    cli = await aiohttp_client(app)
    resp = await cli.get("/status")

    assert await resp.json() == {'status': 'ok'}
