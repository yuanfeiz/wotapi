from pathlib import Path
import rpyc
import time
import asyncio
import random


class DetectorService:
    """
    This service relie on a running cgdetector.x64
    """

    def __init__(self, ip="localhost", port=51237):
        config = {"allow_pickle": True}
        self.rpc = rpyc.connect(ip, port, config=config).root

    def get_info(self):
        return self.rpc.getCamera()

    async def get_progress_events(self):
        """
        Progress events for the detection procedure
        """
        for i in range(100):
            yield i
            wait_for = random.random()
            await asyncio.sleep(wait_for)
