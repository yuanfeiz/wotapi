import pytest
from wotapi.server import setup_app
from pathlib import Path
from aiohttp import web
from configparser import ConfigParser

path = Path(__file__).parent / "resources" / "config.json"
path = path.resolve()


@pytest.fixture
def config():
    config = ConfigParser()
    config.read_dict({"setting_service": {"path": path}})
    return config


async def test_get_settings(aiohttp_client, config):
    app = setup_app(web.Application(), config)
    cli = await aiohttp_client(app)
    resp = await cli.get("/settings")

    expected = {"settings": {"foo": 42}, "meta": {"path": str(path)}}

    assert await resp.json() == expected
