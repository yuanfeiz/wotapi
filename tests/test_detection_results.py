from configparser import ConfigParser, Error
from unittest.mock import AsyncMock, MagicMock, Mock, call

from loguru import logger
from wotapi.services.detection_results import DetectionResultsService
from aiohttp import web
from wotapi.server import setup_app
import pytest

config = ConfigParser()
config.read_dict({
    'detection_results_service': {
        'ROOT_PATH': '/home/yuanfei/projects/siu/wot-core/su/data/timgs'
    },
    'detector_service': {
        "THRESHOLDS": "0,0.92,0.98,0.98"
    }
})


@pytest.fixture
def results_service():
    return DetectionResultsService(config)


@pytest.mark.parametrize('month', ['1', '20200', '202021', 'aaaa0a'])
@pytest.mark.only
async def test_get_results_by_month_invalid_args(
    month, mocker, results_service: DetectionResultsService):
    with pytest.raises(Exception):
        await results_service.get_results_by_month(month)


@pytest.mark.only
async def test_get_results_by_month(mocker,
                                    results_service: DetectionResultsService):
    ret = await results_service.get_results_by_month('202002')
    assert len(ret) > 0
    # using actual file system and real data for testing. the result is not deterministic