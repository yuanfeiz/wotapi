from aiohttp import web
from wotapi.server import setup_app


async def test_get_status(aiohttp_client):
    app = setup_app(web.Application(), {})
    cli = await aiohttp_client(app)
    resp = await cli.get("/status")

    assert await resp.json() == {"status": "ok"}


async def test_delete_auto_mode_task(aiohttp_client, mocker):
    m = mocker.patch("wotapi.services.AutoService.cancel_running_task")
    app = setup_app(web.Application(), {})
    cli = await aiohttp_client(app)
    resp = await cli.delete("/auto/tasks/foo")

    assert await resp.json() == {"status": "ok", "tid": "foo"}
    m.assert_called_with("foo")
