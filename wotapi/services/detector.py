import asyncio
import copy
import shutil
from collections import Counter
from pathlib import Path
from lazy_load import lazy_func, lazy

import rpyc

from wotapi.utils import logger


class DetectorService:
    """
    This service relie on a running cgdetector.x64
    """
    def __init__(self, config):
        self.debug = config.getboolean("global", "DEBUG", fallback=True)
        self.config = config["detector_service"]
        self.thresholds = [
            float(v) for v in self.config.get("THRESHOLDS").split(",")
        ]
        self.conn = self._get_conn()
        self.rpc = lazy(lambda: self.conn.root)

    @lazy_func
    def _get_conn(self):
        # Setup the connection
        host, port = self.config.get('HOST'), self.config.getint('PORT')
        conn = rpyc.connect(
            host,
            port,
            config={
                "allow_pickle":
                True,
                "sync_request_timeout":
                self.config.getint("REQUEST_TIMEOUT", fallback=5),
            },
        )
        logger.info(f'Detector is connected! ({host}:{port})')
        return conn

    def connected(self):
        try:
            self.conn.ping()
            return True
        except Exception:
            host, port = self.config.get('HOST'), self.config.getint('PORT')
            logger.error(f'Detector RPC is down! ({host}:{port})')
            return False

    async def start(self, path, monitor_mode):
        try:
            logger.info(f"start CG detection: {path=}")

            # these calls can be blocking, consider run_in_executor
            self.rpc.stopDetector()
            self.rpc.startDetector(path, monitor_mode)

            p = Path(path)
            for i in range(1, 5):
                child_folder = p / str(i)
                child_folder.mkdir(exist_ok=True)
                logger.info(f"created result folders: {child_folder}")

            counter = Counter()
            progress_value = 0

            while progress_value < 100:
                posi = self.rpc.getPos()
                logger.info(f"{posi=}")

                if posi[1] == -1:
                    continue
                elif posi[1] == 0:
                    logger.info("failed to start the detection, abort")
                    break

                if self.debug:
                    # force advancing
                    progress_value += 3
                else:
                    progress_value = (posi[0] + 1) / posi[1] * 100.0

                logger.info(f"detection progress: {progress_value}")

                data = copy.deepcopy(self.rpc.getResults())
                ldata = len(data)
                logger.info(f"detection result counts: {ldata}")

                for item in data:
                    name, label, confidence_level = item

                    if label == 0:
                        # skip item with label = 0
                        continue

                    logger.info(
                        f"get result item: {name=} {label=} {confidence_level=}"
                    )

                    bname = Path(name).stem
                    logger.info(f"{bname=}")
                    # if item[1] != 0:
                    #     self.m_series[item[1]].append(fpos, item[2])

                    if confidence_level >= self.thresholds[label]:
                        counter[label] += 1

                    pathd = (p / str(label) /
                             f"{ confidence_level }_{bname}.png")
                    paths = path / name
                    shutil.copyfile(paths, pathd)
                    logger.info(f"copy from {paths=} to {pathd=}")
                    # fpos = fpos + 1

                logger.info(f"detection results: {counter}")
                await asyncio.sleep(0.5)

            logger.info(f"completed CG detection: {counter}")
        except Exception as e:
            logger.error(f"failed to run detector: {e}")
        finally:
            await asyncio.sleep(2)
            await self.stop()

    async def stop(self):
        self.rpc.stopDetector()
        logger.info(f"stopped the detector")
