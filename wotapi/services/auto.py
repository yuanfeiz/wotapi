import asyncio
from ..utils import id_factory, logger
import typing
from datetime import datetime, timedelta
from .task import TaskService
from .camera import CameraService
from ..async_pubsub import AMemoryPubSub, AMemorySubscriber

import paco


class AutoService:
    def __init__(self, config, task_service: TaskService,
                 camera_service: CameraService):
        # At most one running task at a time
        self.running_task: asyncio.Task = None
        self.progress: typing.Dict[str, asyncio.Queue] = {}
        self.config = config

        self.cached_results = {
            "past": [
                {
                    "date": "2020-01-21",
                    "result": "k_full"
                },
                {
                    "date": "2020-01-22",
                    "result": "k_none"
                },
            ],
            "today": [],
        }

        self.task_service = task_service
        self.camera_service = camera_service

        self.hub = AMemoryPubSub(asyncio.Queue)

    def calc_interval_and_defer_secs(self,
                                     times_per_day: int = 8
                                     ) -> typing.Tuple[int, int]:
        interval_secs = int(24 * 60 * 60 / times_per_day)

        now = datetime.now()
        tmr = now + timedelta(days=1)
        midnight = tmr.replace(hour=0, second=0, microsecond=0)
        defer_secs = (midnight - now).seconds

        return interval_secs, defer_secs

    async def schedule(
        self, mode: str, **kwargs
    ) -> typing.Tuple[str, AMemorySubscriber, AMemorySubscriber]:
        # do argument checks
        assert mode in ["single", "period", "scheduled"]
        self.cancel_running_task()

        # assign tid for the child scheduler
        tid = id_factory.get()
        # for emitting scheduler events eg. "new batch starts"
        scheduler_sub = await self.hub.subscribe("c_scheduler")
        # for emitting worker events
        worker_sub = await self.hub.subscribe("c_worker")

        if mode == "single":
            self.running_task = self.task_service.create_task(
                self.run_once(), tid)
            logger.info(f"Scheduled autorun {mode=} {self.running_task}")
        elif mode == "period":
            self.running_task = self.task_service.create_task(
                self.run_period(), tid)
            logger.info(f"Scheduled autorun {mode=} {self.running_task}")
        elif mode == "scheduled":
            times = kwargs["times"]
            interval_secs, defer_secs = self.calc_interval_and_defer_secs(
                times)
            self.running_task = self.task_service.create_task(
                self.run_multiple(defer_secs, interval_secs), tid)
            logger.info(
                f"Scheduled autorun {mode=} {self.running_task}, "
                f"will be run in {defer_secs}s and interval is "
                f"{interval_secs}s", )

        return tid, scheduler_sub, worker_sub

    def cancel_running_task(self, tid: str = None):
        logger.debug(f"Cancelling {self.running_task}")
        if self.running_task is not None:
            # Cancel the running task
            self.running_task.cancel()

    async def run_period(self):
        tid = asyncio.current_task().get_name()
        idx = 0

        def event(event, idx, msg=None):
            return {
                "id": tid,
                "event": event,
                "mode": "period",
                "batch": idx,
                'msg': msg
            }

        try:
            await self.hub.publish("c_scheduler", event("start", idx))
            while True:
                logger.info(f"Running #{idx} run_period({tid})")
                await self._run("period", idx)

                # increase run no.
                idx += 1
        except asyncio.CancelledError:
            await self.hub.publish("c_scheduler", event("finish", idx))
            logger.info(f"Stopped run_period({tid}), ran for {idx} times")
        except Exception as e:
            await self.hub.publish("c_scheduler", event("abort", idx, repr(e)))
            logger.info(f'Abort run_period({tid}), ran for {idx} times')
            raise e

    async def run_multiple(self, defer_secs: int, interval_secs: int):
        tid = asyncio.current_task().get_name()
        idx = 0

        def event(event, idx):
            return {
                "id": tid,
                "event": event,
                "mode": "multiple",
                "batch": idx,
            }

        try:
            # TODO: duplicate w/ run_period, requires refactor
            await self.hub.publish("c_scheduler", event("start", idx))

            async def _run_once():
                # start run
                nonlocal idx
                logger.info(f"Running #{idx} run_multiple({tid})")
                await self._run("multiple", idx)

                # finish
                idx += 1

            logger.debug(f"Scheduling run_multiple({tid}) in {defer_secs}s, "
                         f"interval is {interval_secs}s")

            await asyncio.sleep(defer_secs)

            await paco.interval(_run_once, interval=interval_secs)()
        except asyncio.CancelledError:
            await self.hub.publish("c_scheduler", event("finish", idx))
            logger.info(f"Stopped run_multiple({tid}), ran for {idx} times")
        except Exception as e:
            logger.error(e)
            raise e

    async def _run(self, mode: str, idx: int):
        tid = asyncio.current_task().get_name()
        logger.debug(f"running auto mode task({tid}): {mode=}, {idx=}")

        def event(event):
            return {"id": tid, "event": event, "mode": mode, "batch": idx}

        async def consume(q: asyncio.Queue):
            try:
                while True:
                    evt = await q.get()
                    logger.info(f"get c_worker event: {evt}")
                    await self.hub.publish("c_worker", evt)
                    q.task_done()
            except asyncio.CancelledError:
                logger.info(f"consumer stopped")

        await self.hub.publish("c_scheduler", event("start_run"))

        queue = asyncio.Queue()
        # bring up the consumer
        consumer = asyncio.create_task(consume(queue))
        # start auto mode
        await self.camera_service.start_auto_capturing(queue)
        # wait for all events to be consumed
        await queue.join()
        # no events left, shutdown the consumer gracefully
        consumer.cancel()

        await self.hub.publish("c_scheduler", event("finish_run"))

    async def run_once(self):
        await self._run("single", 0)

    async def get_results(self):
        return self.cached_results
