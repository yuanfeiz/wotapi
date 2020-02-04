from wotapi.services.camera import CameraService
from wotapi.services.task import TaskService
from wotapi.services import AutoService
import pytest
import asyncio
from configparser import ConfigParser
from unittest.mock import ANY, MagicMock, Mock

config = ConfigParser()
config.read_dict({
    "auto": {
        "start_auto_mode_script_path": "tests/resources/mock_auto_mode.py"
    }
})


@pytest.fixture()
def auto_service() -> AutoService:
    return AutoService(config, Mock(), Mock())


@pytest.mark.asyncio
async def test_init_auto_service(auto_service):
    assert auto_service is not None


@pytest.mark.parametrize('mode,raised,n', [
    ('once', True, None),
    ('single', False, None),
    ('period', False, None),
    ('scheduled', False, 8),
])
@pytest.mark.asyncio
async def test_schedule_rejects_invalid_mode(mode, raised, n,
                                             auto_service: AutoService,
                                             mocker):
    if raised:
        with pytest.raises(AssertionError):
            await auto_service.schedule(mode)
    else:
        tid, _, _ = await auto_service.schedule(mode, times=n)
        m: MagicMock = auto_service.task_service.create_task
        m.assert_called_once_with(ANY, tid)


@pytest.mark.asyncio
async def test_run_once(mocker):
    camera_srv_mock = MagicMock(CameraService)

    async def produce(queue: asyncio.Queue):
        await queue.put('m')
        await queue.put('a')
        await queue.put('y')

    camera_srv_mock.start_auto_capturing.side_effect = produce

    auto_service = AutoService(config, MagicMock(TaskService), camera_srv_mock)
    sched_sub = await auto_service.hub.subscribe('c_scheduler')
    worker_sub = await auto_service.hub.subscribe('c_worker')

    await auto_service.run_once()

    # check scheduler events
    expected_seq = ['start_run', 'finish_run']
    for evt in expected_seq:
        item = await sched_sub.__anext__()
        assert evt == item['event']
        assert 0 == item['batch']
        assert 'single' == item['mode']
    # drain the queue
    assert sched_sub.messages.qsize() == 0

    # check worker events
    expected_seq = list('may')
    for evt in expected_seq:
        assert evt == await worker_sub.__anext__()
    assert sched_sub.messages.qsize() == 0

    camera_srv_mock.start_auto_capturing.assert_awaited_once()