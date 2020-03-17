import asyncio
import json
import time

import aiofiles

from wotapi.utils import logger

from .sensor_reading import SensorReading


class SensorService:
    def __init__(self, path, sampling_freq=1):
        # The file path where the sensor reading resides
        self.path = path
        # The frequency of sampling(ie. access the reading)
        self.sampling_freq = sampling_freq

    async def get_reading_from_filesystem(self, path):
        async with aiofiles.open(path, "r+") as f:
            content = await f.readlines()
            content = " ".join(content)
            return json.loads(content)

    async def on_reading(self):
        """
        Notify listeners that new reading is available
        """
        wait_for = 1 / self.sampling_freq
        logger.debug(
            f"Start getting sensor reading from {self.path} at {self.sampling_freq}/s"
        )
        ct = 0
        while True:
            try:
                values = await self.get_reading_from_filesystem(self.path)
            except:
                if ct % (10 * self.sampling_freq) == 0:
                    logger.debug('sensor reading except:', ct)
                continue
            yield SensorReading(values=values, timestamp=int(time.time()))
            await asyncio.sleep(wait_for)
            ct = ct + 1
