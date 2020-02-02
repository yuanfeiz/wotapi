import asyncio
import logging
from multiprocessing import queues
from multiprocessing.managers import BaseManager

import math
import rpyc
from tenacity import after_log, retry, retry_if_exception_type, wait_exponential

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
        config,
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
        logger.info(f"RPC connected! ({rpc_host}:{rpc_port})")

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
        self.detector_service = detector_service
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
        """
        Ensure only subscribe stream should be initialized here
        """
        self.intensity_stream = await self.hub.subscribe("intensity")

    async def initiate_capturing(self, settings):
        csettings = settings.get("K_CAPTURING")
        payload = {
            "PSTART": [
                csettings.get("RECORD_RAW"),
                csettings.get("RECORD_PARTICLE"),
            ]
        }
        await self.put_item(self.cmd_queue, payload)
        logger.debug("Requested cqueue to start capturing")

    async def initiate_capturing_script(
        self, settings, script_name: str, queue: asyncio.Queue
    ):
        # Step 2: run the script to start as well
        script_args = {
            "CPZT": ",".join([str(v) for v in settings.get("CPZT")]),
            "LASER": settings.get("LASER"),
            "SPV": ",".join([str(v) for v in settings.get("SPV")]),
        }

        logger.debug(f"Run {script_name} with arguments: {script_args=}")
        return await self.task_service.submit(script_name, queue, **script_args)

    async def start_auto_capturing(self, queue: asyncio.Queue):
        """
        Run the auto mode 

        @todo: move to auto service
        """
        settings = await self.setting_service.get()
        try:
            await self.initiate_capturing(settings)

            async def noop():
                pass

            classify_coro = noop()
            detector_service_connected = self.detector_service.connected()
            if detector_service_connected:
                logger.info("detector is connected, start classifying images")
                # Detector is working, wait for the path to return
                # and start detecting

                # Get the first result path
                sub = await self.hub.subscribe("results_path")
                path = None
                monitor_mode = True
                async for _path in sub:
                    path = _path
                    break

                # Start detector
                classify_coro = self.detector_service.start(path, monitor_mode)

            # submit the task, this doesn't block
            tid = await self.initiate_capturing_script(
                settings, "startautoflow", queue
            )

            # clean up
            # wait for the tasks to be done
            classify_result, script_result = await asyncio.gather(
                classify_coro, self.task_service.running_tasks[tid]
            )
            logger.info(
                f"completed classification and the script: {classify_result=}, {script_result=}"
            )
        except Exception as e:
            logger.error(f"failed to clean up auto mode: {e}")
        finally:
            # shutdown camera
            await asyncio.sleep(5)
            await self.stop_capturing(tid, stop_script_name="stopautoflow")

            # shutdown detector
            if detector_service_connected:
                await asyncio.sleep(5)
                await self.detector_service.stop()
                logger.info(f"shutdown detector")

    async def start_manual_capturing(self) -> (str, asyncio.Queue):
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

        exit_code = await self.task_service.cancel(tid, stop_script_filename)
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
