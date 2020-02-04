from configparser import ConfigParser
from unittest.mock import AsyncMock, MagicMock, Mock, call
from wotapi.services.detector import DetectorService
from aiohttp import web
from wotapi.server import setup_app
import pytest


def test_lazily_create_rpc(mocker):
    m: Mock = mocker.patch('rpyc.connect')

    # Not connect during when it's only created
    srv = DetectorService(MagicMock())
    m.assert_not_called()

    # Connect only when it's referenced
    srv.conn.ping()
    m.assert_called_once()