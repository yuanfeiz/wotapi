from pathlib import Path
import logging
import rpyc
import time
import asyncio
import random

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


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


# if __name__ == "__main__":
    # sample_path = Path("/projects/siu/wot/wotapi/data/")

    # ds = DetectorService()

    # ds.rpc.stopDetector()
    # ds.rpc.startDetector(str(sample_path), True)

    # while True:
    #     logging.info(f"{ds.rpc.getPos()=}")
    #     logging.info(f"{ds.rpc.getResults()=}")
    #     time.sleep(0.5)
