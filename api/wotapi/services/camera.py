from wotapi.utils import config
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
            queue_config.get("port"),
            queue_config.get("authkey").encode("utf8"),
        )
        status_queue_name, command_queue_name = (
            queue_config.get("status_queue_name"),
            queue_config.get("command_queue_name"),
        )

        self.rpc = rpyc.connect(rpc_host, rpc_port).root

        CameraQueueManager.register(status_queue_name)
        CameraQueueManager.register(command_queue_name)
        self.queue_mgr = CameraQueueManager((queue_host, queue_port), authkey=authkey)

    def get_info(self):
        return self.rpc.getCamera()
