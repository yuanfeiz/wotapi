import asyncio
import random
from ..utils import id_factory, logger
import time
import typing
from datetime import datetime, timedelta
import sys

import paco


class AutoService:
    def __init__(self, config):
        # At most one running task at a time
        self.running_task: asyncio.Task = None
        self.progress: typing.Dict[str, asyncio.Queue] = {}
        self.config = config

        now = time.time()
        self.cached_results = {
            "past": [
                {"date": "2020-01-21", "result": "k_full"},
                {"date": "2020-01-22", "result": "k_none"},
            ],
            "today": [],
        }

    async def schedule_run_once(self) -> (str, asyncio.Task, asyncio.Queue):
        self.cancel_running_task()
        logger.info(f"Canceled the running task")
        tid = id_factory.get()
        q = asyncio.Queue()
        self.running_task = asyncio.create_task(self.run_once(tid, q))
        logger.info(f"Scheduled run_once {self.running_task}")
        return tid, self.running_task, q

    async def schedule_run_period(self) -> (str, asyncio.Task, asyncio.Queue):
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

    async def schedule_run_multiple(
        self, times_per_day: int = 8
    ) -> (str, asyncio.Task, asyncio.Queue):
        self.cancel_running_task()
        logger.info(f"Canceled the running task")

        # interval_secs = 24 * 60 * 60 / times_per_day
        interval_secs = times_per_day

        now = datetime.now()
        tmr = now + timedelta(days=1)
        midnight = tmr.replace(hour=0, second=0, microsecond=0)
        defer_secs = (midnight - now).seconds
        defer_secs = 0

        tid = id_factory.get()
        q = asyncio.Queue()
        self.running_task = asyncio.create_task(
            self.run_multiple(tid, defer_secs, interval_secs, q)
        )
        logger.info(
            f"Scheduled run_multiple {self.running_task}, will be run in {defer_secs}s and interval is {interval_secs}s"
        )
        return tid, self.running_task, q

    def cancel_running_task(self, tid: str = None):
        logger.debug(f"Cancelling {self.running_task}")
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

    async def run_multiple(
        self, tid, defer_secs: int, interval_secs: int, queue: asyncio.Queue
    ):
        try:

            # TODO: duplicate w/ run_period, requires refactor
            idx = 0

            async def _run_once():
                nonlocal idx
                logger.info(f"Running #{idx} run_multiple({tid})")
                ret = await self.run_once(tid)
                await queue.put(ret)
                idx += 1

            logger.debug(
                f"Scheduling run_multiple({tid}) in {defer_secs}s, interval is {interval_secs}s"
            )

            await asyncio.sleep(defer_secs)

            await paco.interval(_run_once, interval=interval_secs)()
        except asyncio.CancelledError:
            logger.info(f"Stopped run_multiple({tid}), ran for {idx} times")
        except Exception as e:
            logger.error(e)
            raise e

    async def _run(self, path, queue: asyncio.Queue):
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-u", path, stdout=asyncio.subprocess.PIPE
        )
        logger.debug(f"Start executing {path}")
        while not proc.stdout.at_eof():
            data = await proc.stdout.readline()
            line = data.decode("utf8").strip()
            logger.debug(f"Read line {line}, put to the queue")
            await queue.put(line)
        return proc

    async def run_once(self, tid, queue: asyncio.Queue):
        try:
            started_at = time.time()
            path = self.config.get("auto", "start_auto_mode_script_path",)

            # Run and wait for the process to finish
            proc = await self._run(path, queue)
            await proc.wait()

            # Mocks
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
            # Terminate the process if it's cancelled
            await proc.terminate()
            logger.info(f"Stopped run_once({tid})")
            # reraise to propogate this cancel to run_period
            raise e

    async def get_results(self):
        return self.cached_results

