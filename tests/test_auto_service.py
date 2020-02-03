from wotapi.services import AutoService
import pytest
import asyncio
from configparser import ConfigParser
from unittest.mock import AsyncMock, Mock

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
async def test_run_once_yield_subprocess_stdout(auto_service: AutoService,
                                                mocker):
    q = asyncio.Queue()

    async def _test_queue(q):
        assert (await q.get()) == "START"
        for i in range(5):
            assert (await q.get()).startswith("STAT:AL")

    ret = await asyncio.gather(auto_service.run_once("foo", q), _test_queue(q))

    assert ret[0]["id"] == "foo"


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
