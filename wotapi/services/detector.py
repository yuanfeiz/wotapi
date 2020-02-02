from pathlib import Path
import rpyc
import time
import asyncio
import random
from wotapi.utils import logger


class DetectorService:
    """
    This service relie on a running cgdetector.x64
    """

    def __init__(self, config):
        self.config = config["detector_service"]

        # Setup the connection
        self._conn = rpyc.connect(
            self.config["HOST"],
            self.config.getint("PORT"),
            config={
                "allow_pickle": True,
                "sync_request_timeout": self.config.getint(
                    "REQUEST_TIMEOUT", fallback=5
                ),
            },
        )

        # Check if detector is connected
        if self.connected():
            logger.info(
                f'Detector connected! ({self.config["HOST"]}:{self.config["PORT"]})'
            )

        self.rpc = self._conn.root

    def connected(self):
        try:
            # ping the service and wait for at most 1s
            self._conn.ping(timeout=1)
            return True
        except Exception as e:
            logger.error(f"failed to connect to the detector: {e}")
            return False
