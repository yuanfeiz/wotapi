from configparser import ConfigParser
from unittest.mock import AsyncMock, MagicMock, Mock, call
from wotapi.models import TaskState
from aiohttp import web
from wotapi.server import setup_app
import pytest
import time

config = ConfigParser()
config.read('config.test.ini')


@pytest.mark.parametrize('action,args,ok', [('infuse', [7, 13], True),
                                            ('withdraw', [7, 13], True),
                                            ('stop', [], True),
                                            ('invalid_operation', [], False)])
async def test_control_syringe_pump(action, args, ok, aiohttp_client, mocker):
    mocker.patch('wotapi.server.sanity_check')
    mocker.patch('wotapi.server.setup_feeds')
    mocker.patch('wotapi.services.SettingService.get',
                 return_value={'SPV': [7, 13]})
    m: AsyncMock = mocker.patch('wotapi.services.TaskService._run_script',
                                return_value=0)
    app = setup_app(web.Application(), config)
    cli = await aiohttp_client(app)
    resp = await cli.post("/tasks/capturing/syringe_pump",
                          json={'value': action})

    if not ok:
        assert resp.status == 500
        return

    resp_json = await resp.json()
    assert TaskState(resp_json['state']) == TaskState.Completed
    assert 'id' in resp_json
    assert time.time() - resp_json['startedAt'] < 1

    m.assert_awaited_once_with('spcontrol.py', None, _=[action, *args])


async def test_control_syringe_pump_exit_code_not_zero(aiohttp_client, mocker):
    mocker.patch('wotapi.server.sanity_check')
    mocker.patch('wotapi.server.setup_feeds')
    mocker.patch('wotapi.services.SettingService.get',
                 return_value={'SPV': [7, 13]})
    m: AsyncMock = mocker.patch('wotapi.services.TaskService._run_script',
                                side_effect=Exception('flying bug'))

    app = setup_app(web.Application(), config)
    cli = await aiohttp_client(app)
    resp = await cli.post("/tasks/capturing/syringe_pump",
                          json={'value': 'infuse'})

    resp_json = await resp.json()
    assert TaskState(resp_json['state']) == TaskState.Failed
    assert resp.status == 500