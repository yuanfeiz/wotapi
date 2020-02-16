import asyncio
from configparser import ConfigParser
import logging
from queue import Empty, Queue
from multiprocessing.managers import BaseManager
from contextlib import contextmanager

import math
import rpyc
from tenacity import (
    after_log,
    retry,
    retry_if_exception_type,
    wait_exponential,
)
from typing import Tuple
from lazy_load import lazy_func, lazy

from wotapi.async_pubsub import AMemoryPubSub
from wotapi.utils import logger

from .setting import SettingService
from .task import TaskService
from .detector import DetectorService


class CameraQueueManager(BaseManager):
    pass


class CameraService:
    """
    Camera of the detector, control via RPC.
    This service relies on a running detection.x64 
    """
    def __init__(
        self,
        task_service: TaskService,
        setting_service: SettingService,
        detector_service: DetectorService,
        config: ConfigParser,
    ):
        # Hub for PubSub
        self.hub = AMemoryPubSub(asyncio.Queue)

        self.task_service = task_service
        self.setting_service = setting_service
        self.detector_service = detector_service

        self.rpc_conn = self._get_rpc_conn(config['camera_rpc'])
        self.rpc = lazy(lambda: self.rpc_conn.root)

        self.queue_mgr = self._get_queue_mgr(config["camera_queue"])
        self.status_queue = lazy(lambda: self.queue_mgr.status_queue())
        self.cmd_queue = lazy(lambda: self.queue_mgr.cmd_queue())
        logger.info(
            f'qmgr should be lazily evaludated, not connected at this moment')

        self.config = config['camera_rpc']

    @lazy_func
    def _get_queue_mgr(self, queue_config):
        queue_host, queue_port, authkey = (
            queue_config.get("host"),
            queue_config.getint("port"),
            queue_config.get("authkey").encode("utf8"),
        )
        status_queue_name, cmd_queue_name = (
            queue_config.get("status_queue_name"),
            queue_config.get("cmd_queue_name"),
        )

        CameraQueueManager.register(status_queue_name)
        CameraQueueManager.register(cmd_queue_name)
        mgr = CameraQueueManager((queue_host, queue_port), authkey=authkey)

        # expensive!
        mgr.connect()
        logger.info(f"Queues connected! ({queue_host}:{queue_port})")
        return mgr

    def connected(self) -> bool:
        # Check RPC status
        try:
            self.rpc_conn.ping()
        except Exception as e:
            logger.error(f'Camera RPC is down! {e}')
            return False

        # Check queue status
        try:
            self.queue_mgr.connect()
        except Exception as e:
            logger.error(f'Camera QUEUE is down! ({e})')
            return False

        return True

    @lazy_func
    def _get_rpc_conn(self, rpc_config):
        rpc_host, rpc_port = rpc_config.get("host"), rpc_config.getint("port")

        conn = rpyc.connect(rpc_host, rpc_port)
        logger.info(f'Camera RPC connected! ({rpc_host}:{rpc_port})')
        return conn

    def get_info(self):
        return self.rpc.getCamera()

    @retry(
        wait=wait_exponential(multiplier=0.5, max=60),
        retry=retry_if_exception_type(Empty),
        # before_sleep=before_sleep_log(logger, logging.DEBUG),
    )
    async def get_item(self, queue: Queue):
        return queue.get_nowait()

    @retry(
        wait=wait_exponential(max=60),
        after=after_log(logger, logging.DEBUG),
    )
    async def put_item(self, queue: Queue, item):
        logger.info(f"send command: {item=}")
        return queue.put_nowait(item)

    async def emit_status_queue_item(self):
        # Start receiving item from RPC calls
        try:
            while True:
                item = await self.get_item(self.status_queue)
                if item == '--EOF--':
                    break
                # logger.debug(f"Get squeue item: keys={item.keys()}")

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
                    logger.info(f'get results path: {item["SPATH"]}')
                    await self.hub.publish("results_path", item["SPATH"])
                else:
                    logger.info(f"get unhandled item: {item}")

                wait_for = float(self.config.get("QUEUE_CONSUME_RATE"))
                await asyncio.sleep(wait_for)
        except asyncio.CancelledError:
            logger.info('stopped pub squeue items')
            raise

    async def init_subscribers(self):
        """
        Ensure only subscribe stream should be initialized here
        """
        self.intensity_stream = await self.hub.subscribe("intensity")

    async def initiate_capturing(self, settings):
        csettings = settings.get("imaging")
        payload = {
            "PSTART": [
                csettings.get("record.raw"),
                csettings.get("record.particle"),
            ]
        }
        await self.put_item(self.cmd_queue, payload)
        logger.info("Requested cqueue to start capturing")

    async def initiate_capturing_script(self, settings, script_name: str,
                                        queue: asyncio.Queue):
        # Step 2: run the script to start as well
        script_args = {
            "CPZT":
            f"{settings['capturing']['pzt.freq']},{settings['capturing']['pzt.voltage']}",
            "LASER":
            settings['capturing']['laser.current'],
            "SPV":
            f'{settings["capturing"]["syringe.flow"]},{settings["capturing"]["syringe.volume"]}'
        }

        logger.debug(f"Run {script_name} with arguments: {script_args=}")
        return await self.task_service.create_script_task(
            script_name, queue, **script_args)

    async def start_auto_capturing(self, queue: asyncio.Queue):
        """
        Run the auto mode 

        @todo: move to auto service
        """
        settings = await self.setting_service.get()

        # Start capturing particle
        await self.initiate_capturing(settings)

        # Submit the task, this doesn't block
        tid = await self.initiate_capturing_script(settings, "startautoflow",
                                                   queue)
        detector_service_connected = self.detector_service.connected()
        classify_task = None

        try:
            if detector_service_connected:
                logger.info("detector is connected, try classifying images")
                # Detector is working, wait for the path to return
                # and start detecting
                sub = await self.hub.subscribe("results_path")
                monitor_mode = True
                try:
                    # Get the first result path
                    logger.info(f'waiting for the result path')
                    path = await asyncio.wait_for(sub.__anext__(), timeout=3)
                    logger.info(
                        f"get results_path {path}, starting classifier")
                    # Start detector
                    classify_coro = self.detector_service.start(
                        path, monitor_mode)
                    classify_task = asyncio.create_task(classify_coro)
                except asyncio.TimeoutError:
                    logger.error('get results_path timeout(3s)')
                    detector_service_connected = False

            # clean up
            # wait for the tasks to be done
            script_result = await self.task_service.running_tasks[tid]
            logger.info(f"completed script: {script_result=}")
            await asyncio.sleep(5)
        except Exception as e:
            logger.exception(f"failed to clean up auto mode: {e}")
        finally:
            # shutdown camera
            await self.stop_capturing(tid, stop_script_name="stopautoflow")

            # shutdown detector
            if detector_service_connected and classify_task is not None:
                await asyncio.sleep(3)
                classify_task.cancel()
                try:
                    await classify_task
                except asyncio.CancelledError:
                    logger.info('Classification task is cancelled')

            logger.info('completed start autoflow task')

    async def start_manual_capturing(self) -> Tuple[str, asyncio.Queue]:
        settings = await self.setting_service.get()
        queue = asyncio.Queue()

        # Step 1: send item to cqueue requesting start capturing
        await self.initiate_capturing(settings)
        tid = await self.initiate_capturing_script(settings, "mfs_pd", queue)

        return tid, queue

    async def stop_capturing(self, tid: str, stop_script_name="mfs_stop"):
        payload = {"PSTOP": 1}
        await self.put_item(self.cmd_queue, payload)
        logger.info("Requested cqueue to stop capturing")

        exit_code = await self.task_service.cancel(tid, stop_script_name)
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
