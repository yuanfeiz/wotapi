from configparser import ConfigParser
from unittest.mock import AsyncMock, MagicMock, Mock, call
from wotapi.models import TaskState
from aiohttp import web
from wotapi.server import setup_app
import pytest
import time

config = ConfigParser()
config.read('config.test.ini')


# @pytest.mark.only
async def test_control_syringe_pump(aiohttp_client, mocker):
    mocker.patch('wotapi.server.sanity_check')
    mocker.patch('wotapi.server.setup_feeds')
    mocker.patch('wotapi.services.SettingService.get',
                 return_value={'SPV': [7, 13]})
    app = setup_app(web.Application(), config)
    cli = await aiohttp_client(app)
    resp = await cli.post("/tasks/capturing/syringe_pump",
                          json={'value': 'infuse'})

    resp_json = await resp.json()
    assert TaskState(resp_json['state']) == TaskState.Completed
    assert 'id' in resp_json
    assert time.time() - resp_json['startedAt'] < 1
