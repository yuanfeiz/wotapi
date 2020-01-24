import pytest
from wotapi.server import setup_app
from aiohttp import web


async def sum(a, b):
    return a + b


@pytest.mark.asyncio
async def test_get_status(aiohttp_client):
    app = setup_app(web.Application()) 
    resp = await app.get('/status')
    assert resp == None
    assert await sum(1, 1) == 2
