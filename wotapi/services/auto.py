import asyncio
import random
from ..utils import id_factory, logger
import time


class AutoService:
    def __init__(self):
        # At most one running task at a time
        self.running_task: asyncio.Task = None

        now = time.time()
        self.cached_results = {
            "past": [
                {"date": "2020-01-21", "result": "k_full"},
                {"date": "2020-01-22", "result": "k_none"},
            ],
            "today": [
            ],
        }

    async def schedule_run_once(self) -> (str, asyncio.Task):
        self.cancel_running_task()
        logger.info(f"Canceled the running task")
        tid = id_factory.generate()
        self.running_task = asyncio.create_task(self.run_once(tid))
        logger.info(f"Scheduled run_once")
        return tid, self.running_task

    async def schedule_run_period(self) -> (str, asyncio.Task):
        return id_factory.generate(), self.running_task

    async def schedule_run_multiple(self, times: int) -> (str, asyncio.Task):
        return id_factory.generate(), self.running_task

    def cancel_running_task(self):
        if self.running_task is not None:
            # Cancel the running task
            self.running_task.cancel()

    async def run_once(self, tid):
        started_at = time.time()
        for i in range(5):
            logger.info(f"Emitting run_once number: {i}")
            await asyncio.sleep(1)

        ret = {
            "id": tid,
            # TODO: set mode
            "mode": "",
            "startedAt": started_at,
            "values": {"crypto": random.random() * 4, "giardia": random.random() * 3},
            "finishedAt": time.time(),
        }

        self.cached_results["today"].append(ret)

        return ret

    async def get_results(self):
        return self.cached_results

