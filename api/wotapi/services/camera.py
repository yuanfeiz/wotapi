from wotapi.utils import config, logger
from multiprocessing.managers import BaseManager
from numpngw import write_png
import time
import rpyc
import numpy as np


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

    def get_info(self):
        return self.rpc.getCamera()
