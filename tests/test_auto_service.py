from wotapi.services.camera import CameraService
from wotapi.services.task import TaskService
from wotapi.services import AutoService
import pytest
import asyncio
from configparser import ConfigParser
from unittest.mock import AsyncMock, MagicMock, Mock

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


@pytest.mark.asyncio
async def test_schedule_run_once(auto_service: AutoService, mocker):
    """
    Simply run the procedure for once
    """
    mock_run = mocker.patch.object(auto_service,
                                   "_run",
                                   new_callable=AsyncMock)
    tid, task, q = await auto_service.schedule_run_once()
    assert isinstance(tid, str)
    assert len(tid) > 0

    res = (await auto_service.get_results())["today"]
    prev_len = len(res)

    await task
    assert task.done()

    res = (await auto_service.get_results())["today"]
    assert len(res) == prev_len + 1


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


@pytest.mark.skip("only run to figure out the mechenism")
@pytest.mark.asyncio
async def test_vanilla_run_once():
    import sys

    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "tests/resources/mock_auto_mode.py",
        stdout=asyncio.subprocess.PIPE,
    )
    while not proc.stdout.at_eof():
        data = await proc.stdout.readline()
        line = data.decode("utf8").strip()
        print(line, flush=True)
    assert proc == None
