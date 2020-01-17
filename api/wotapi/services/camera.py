from wotapi.utils import config, logger
from multiprocessing.managers import BaseManager
from numpngw import write_png
import time
import rpyc
import numpy as np
from aioify import aioify
import asyncio
from aio_pubsub.backends.memory import MemoryPubSub, MemorySubscriber
import paco


class AMemorySubscriber(MemorySubscriber):
    async def __anext__(self):
        return await self.messages.get()


class AMemoryPubSub(MemoryPubSub):
    async def subscribe(self, channel: str):
        subscriber = AMemorySubscriber(self.queue_factory)
        self.subscribers[channel].add(subscriber)
        return subscriber


class CameraQueueManager(BaseManager):
    pass


class CameraService:
    """
    Camera of the detector, control via RPC.
    This service relies on a running detection.x64 
    """

    def __init__(self):
        # TODO: inject rpc and queue_mgr
        rpc_config = config["camera_rpc"]
        rpc_host, rpc_port = rpc_config.get("host"), rpc_config.get("port")

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
        self.queue_mgr = CameraQueueManager((queue_host, queue_port), authkey=authkey)
        self.queue_mgr.connect()
        logger.info(f"Queues connected! ({queue_host}:{queue_port})")

        self.status_queue = self.queue_mgr.status_queue()
        self.cmd_queue = self.queue_mgr.cmd_queue()

        # Hub for PubSub
        self.hub = AMemoryPubSub(asyncio.Queue)

        # TODO: default to NullSubscriber
        self.image_stream = None
        self.intensity_stream = None

    def get_info(self):
        return self.rpc.getCamera()


    async def connect(self):
        # Start receiving item from RPC calls
        while True:
            item = await paco.wraps(self.status_queue.get)()

            # Distribute item according to its topic
            if "CIMG" in item or "TIMG" in item:
                await self.hub.publish("image", item)
            elif "INT" in item:
                await self.hub.publish("intensity", {
                    'samples': item['INT'],
                    'stats': {
                        'fps': item['ISTAT'][0],
                        'lptc': item['ISTAT'][1]
                    }
                })

            await asyncio.sleep(0.5)

    async def init_subscribers(self):
        self.image_stream = await self.hub.subscribe("image")
        self.intensity_stream = await self.hub.subscribe("intensity")

