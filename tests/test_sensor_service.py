import pytest
from wotapi.services import SensorService
from wotapi.services.sensor_reading import SensorReading
from pathlib import Path
import time


@pytest.mark.asyncio
async def test_async_get_readings():
    filename = str((Path(__file__).parent / "resources" / "dfppmgui.json").resolve())
    sample_rate = 5
    srv = SensorService(filename, sample_rate)

    start = time.monotonic()
    idx = 0
    async for r in srv.on_reading():
        assert isinstance(r, SensorReading)
        assert "PS1" in r.values

        idx += 1
        if idx == 2:
            break
    assert time.monotonic() - start > (1 / sample_rate)
