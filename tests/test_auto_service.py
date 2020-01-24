from wotapi.services import AutoService
import pytest
from asyncmock import AsyncMock
from unittest.mock import patch
import asyncio


@pytest.fixture()
def auto_service() -> AutoService:
    return AutoService()


@pytest.mark.asyncio
async def test_init_auto_service(auto_service):
    assert auto_service is not None


@pytest.mark.asyncio
async def test_schedule_run_once(auto_service: AutoService, mocker):
    """
    Simplely run the procedure for once
    """
    sleep = mocker.patch("asyncio.sleep", new_callable=AsyncMock)
    tid, task = await auto_service.schedule_run_once()
    assert isinstance(tid, str)
    assert len(tid) > 0

    res = (await auto_service.get_results())['today']
    prev_len = len(res)

    await task
    assert task.done()

    res = (await auto_service.get_results())['today']
    assert len(res) == prev_len + 1
