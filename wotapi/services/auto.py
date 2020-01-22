import asyncio
import random
from ..utils import id_factory, logger
import time
import typing


class AutoService:
    def __init__(self):
        # At most one running task at a time
        self.running_task: asyncio.Task = None
        self.progress: typing.Dict[str, asyncio.Queue] = {}

        now = time.time()
        self.cached_results = {
            "past": [
                {"date": "2020-01-21", "result": "k_full"},
                {"date": "2020-01-22", "result": "k_none"},
            ],
            "today": [],
        }

    async def schedule_run_once(self) -> (str, asyncio.Task):
        self.cancel_running_task()
        logger.info(f"Canceled the running task")
        tid = id_factory.get()
        self.running_task = asyncio.create_task(self.run_once(tid))
        logger.info(f"Scheduled run_once {self.running_task}")
        return tid, self.running_task

    async def schedule_run_period(self) -> (str, asyncio.Task):
        """
        Scheduled a new run on the previous run finished.
        """
        self.cancel_running_task()
        logger.info(f"Canceled the running task")
        tid = id_factory.get()
        q = asyncio.Queue()
        self.running_task = asyncio.create_task(self.run_period(tid, q))
        logger.info(f"Scheduled run_period {self.running_task}")
        return tid, self.running_task, q

    async def schedule_run_multiple(self, times: int) -> (str, asyncio.Task):
        return id_factory.get(), self.running_task

    def cancel_running_task(self, tid: str = None):
        logger.debug(f'Cancelling {self.running_task}')
        if self.running_task is not None:
            # Cancel the running task
            self.running_task.cancel()

    async def run_period(self, tid, queue: asyncio.Queue):
        try:
            idx = 0
            while True:
                logger.info(f"Running #{idx} run_period({tid})")
                ret = await self.run_once(tid)
                # TODO: check memory leaks
                await queue.put(ret)
                idx += 1
        except asyncio.CancelledError:
            logger.info(f"Stopped run_period({tid}), ran for {idx} times")

    async def run_once(self, tid):
        try:
            started_at = time.time()
            for i in range(5):
                logger.info(f"Emitting run_once number: {i}")
                await asyncio.sleep(1)

            ret = {
                "id": tid,
                # TODO: set mode
                "mode": "",
                "startedAt": started_at,
                "values": {
                    "crypto": random.random() * 4,
                    "giardia": random.random() * 3,
                },
                "finishedAt": time.time(),
            }

            self.cached_results["today"].append(ret)

            return ret
        except asyncio.CancelledError as e:
            logger.info(f"Stopped run_once({tid})")
            # reraise to propogate this cancel to run_period 
            raise e 

    async def get_results(self):
        return self.cached_results

