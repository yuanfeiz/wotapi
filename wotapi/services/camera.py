import asyncio
import logging
import typing
from multiprocessing import queues
from multiprocessing.managers import BaseManager

import math
import numpy as np
import rpyc
from json_tricks import dumps
from tenacity import after_log, retry, retry_if_exception_type, wait_exponential

from wotapi.async_pubsub import AMemoryPubSub
from wotapi.utils import logger

from .setting import SettingService
from .task import TaskService


class CameraQueueManager(BaseManager):
    pass


class CameraService:
    """
    Camera of the detector, control via RPC.
    This service relies on a running detection.x64 
    """

    def __init__(
        self, task_service: TaskService, setting_service: SettingService, config
    ):
        # TODO: inject rpc and queue_mgr
        rpc_config = config["camera_rpc"]
        rpc_host, rpc_port = rpc_config.get("host"), rpc_config.getint("port")

        queue_config = config["camera_queue"]
        queue_host, queue_port, authkey = (
            queue_config.get("host"),
            queue_config.getint("port"),
            queue_config.get("authkey").encode("utf8"),
        )
        status_queue_name, cmd_queue_name = (
            queue_config.get("status_queue_name"),
            queue_config.get("cmd_queue_name"),
        )

        self.rpc = rpyc.connect(rpc_host, rpc_port).root
        logger.info(f"RPC connected! ({rpc_host}:{rpc_port})", stack_info=True)

        CameraQueueManager.register(status_queue_name)
        CameraQueueManager.register(cmd_queue_name)
        # TODO: make queue_mgr a local variable
        self.queue_mgr = CameraQueueManager(
            (queue_host, queue_port), authkey=authkey
        )
        self.queue_mgr.connect()
        logger.info(f"Queues connected! ({queue_host}:{queue_port})")

        self.status_queue = self.queue_mgr.status_queue()
        self.cmd_queue = self.queue_mgr.cmd_queue()

        # Hub for PubSub
        self.hub = AMemoryPubSub(asyncio.Queue)

        self.task_service = task_service
        self.setting_service = setting_service
        self.config = config

    def get_info(self):
        return self.rpc.getCamera()

    @retry(
        wait=wait_exponential(max=60),
        retry=retry_if_exception_type(queues.Empty),
        after=after_log(logger, logging.DEBUG),
    )
    async def get_item(self, queue: queues.Queue):
        return queue.get_nowait()

    @retry(
        wait=wait_exponential(max=60), after=after_log(logger, logging.DEBUG),
    )
    async def put_item(self, queue: queues.Queue, item):
        logger.debug(f"send command: {item=}")
        return queue.put_nowait(item)

    async def emit_status_queue_item(self):
        # Start receiving item from RPC calls
        while True:
            item = await self.get_item(self.status_queue)
            logger.debug(f"Get squeue item: keys={item.keys()}")

            # Distribute item according to its topic
            if "CIMG" in item or "TIMG" in item:
                await self.hub.publish("image", item)
            elif "INT" in item:
                await self.hub.publish(
                    "intensity",
                    {
                        "samples": item["INT"][0],
                        "stats": {
                            "fps": item["ISTAT"][0],
                            "lptc": item["ISTAT"][1],
                        },
                    },
                )
            elif "SPATH" in item:
                await self.hub.publish("results_path", item["SPATH"])

            await asyncio.sleep(
                self.config.getfloat("camera_rpc", "QUEUE_CONSUME_RATE")
            )

    async def emit_command_queue_item(self):
        while True:
            item = await self.get_item(self.cmd_queue)
            logger.debug(f"Get cqueue item: keys={item.keys()}")
            await self.hub.publish("camera_info", item)
            await asyncio.sleep(0.5)

    async def init_subscribers(self):
        self.image_stream = await self.hub.subscribe("image")
        self.intensity_stream = await self.hub.subscribe("intensity")

    async def start_capturing(self) -> (str, asyncio.Queue):
        # Step 1: send item to cqueue requesting start capturing
        settings = await self.setting_service.get()
        csettings = settings.get("K_CAPTURING")
        payload = {
            "PSTART": [
                csettings.get("RECORD_RAW"),
                csettings.get("RECORD_PARTICLE"),
            ]
        }
        await self.put_item(self.cmd_queue, payload)
        logger.debug("Requested cqueue to start capturing")

        script_args = {
            "CPZT": ",".join([str(v) for v in settings.get("CPZT")]),
            "LASER": settings.get("LASER"),
            "SPV": ",".join([str(v) for v in settings.get("SPV")]),
        }

        logger.debug(f"Run startcap script with arguments: {script_args=}")

        # Step 2: run the script to start as well
        queue = asyncio.Queue()
        return (
            await self.task_service.submit("mfs_pd", queue, **script_args),
            queue,
        )

    async def stop_capturing(self, tid: str):
        payload = {"PSTOP": 1}
        await self.put_item(self.cmd_queue, payload)
        logger.info("Requested cqueue to stop capturing")

        exit_code = await self.task_service.cancel(tid, "mfs_stop")
        logger.debug(f"Ran stopcap script: {exit_code=}")
        return exit_code

    async def update_intensity_levels(self, low: int, high: int):
        logger.info(f"Updated intensity levels: {low=} {high=}")
        return await self.put_item(self.cmd_queue, {"PICH": [low, high]})

    async def update_camera_exp(self, exposure: float):
        min_val, max_val = self.get_info()["EXP"]
        dv = (math.log(max_val) - math.log(min_val)) / 99.0
        adjusted_exposure = math.exp(math.log(min_val) + (dv * exposure))

        adjusted_exposure = min(int(adjusted_exposure), max_val)
        self.rpc.setExp(adjusted_exposure)
        logger.info(f"Updated camera {exposure=} {adjusted_exposure=}")

    async def update_camera_gain(self, gain: float):
        min_val, max_val = self.get_info()["GAIN"]

        adjusted_gain = gain * (max_val - min_val) / 99.0 + min_val
        adjusted_gain = min(adjusted_gain, max_val)
        self.rpc.setGain(adjusted_gain)
        logger.info(f"Updated camera {gain=} {adjusted_gain=}")

    async def reset_particle_count(self):
        await self.put_item(self.cmd_queue, {"RSCNT": 1})
