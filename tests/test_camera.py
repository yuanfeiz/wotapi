from configparser import ConfigParser
from unittest.mock import AsyncMock, MagicMock, Mock, call
from wotapi.services.camera import CameraQueueManager, CameraService
from aiohttp import web
from wotapi.server import setup_app
import pytest


def test_lazily_connect_rpc(mocker):
    m: Mock = mocker.patch('rpyc.connect')

    # Not connect during when it's only created
    srv = CameraService(Mock(), Mock(), Mock(0), MagicMock())
    m.assert_not_called()

    # Connect only when it's referenced
    srv.rpc.getCamera()
    m.assert_called_once()


def test_lazy_connect_queues(mocker):
    mc: Mock = mocker.patch(
        'wotapi.services.camera.CameraQueueManager.connect')
    mr: Mock = mocker.patch(
        'wotapi.services.camera.CameraQueueManager.register')
    config_mock = MagicMock(ConfigParser)

    srv = CameraService(Mock(), Mock(), Mock(0), config_mock)
    mc.assert_not_called()

    setattr(CameraQueueManager, 'status_queue', MagicMock())
    setattr(CameraQueueManager, 'cmd_queue', MagicMock())

    srv.status_queue.get()
    mc.assert_called_once()
    srv.cmd_queue.get()
    mc.assert_called_once()
    mr.assert_called()