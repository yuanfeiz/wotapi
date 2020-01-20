from wotapi.services.sensor_reading import SensorReading
import aiofiles
import json
import asyncio
from wotapi.utils import logger
import time


class SensorService:
    def __init__(self, path, sampling_freq=1):
        # The file path where the sensor reading resides
        self.path = path
        # The frequency of sampling(ie. access the reading)
        self.sampling_freq = sampling_freq

    async def get_reading_from_filesystem(self, path):
        async with aiofiles.open(path, "r+") as f:
            content = await f.readline()
            return json.loads(content)

    async def on_reading(self):
        """
        Notify listeners that new reading is available
        """
        wait_for = 1 / self.sampling_freq
        logger.debug(f"Start getting sensor reading: {self.path} {self.sampling_freq}")
        while True:
            values = await self.get_reading_from_filesystem(self.path)
            yield SensorReading(values=values, timestamp=int(time.time()))
            await asyncio.sleep(5)
