import asyncio
from configparser import Error
import copy
import shutil
from collections import Counter
from pathlib import Path
from typing import MutableMapping, Union
from wotapi.models import EventLogType, EventTopics, TaskState
from lazy_load import lazy_func, lazy
from ..async_pubsub import AMemoryPubSub
from aio_pubsub.interfaces import PubSub
from itertools import groupby

import rpyc

from wotapi.utils import logger


class DetectorService:
    """
    This service relie on a running cgdetector.x64
    """

    label_txt_mappings = ['others', 'crypto', 'glardia', 'beads']

    def __init__(self, config):
        self.debug = config.getboolean("global", "DEBUG", fallback=True)
        self.config = config["detector_service"]
        self.thresholds = [
            float(v) for v in self.config.get("THRESHOLDS").split(",")
        ]
        self.conn = self._get_conn()
        self.rpc = lazy(lambda: self.conn.root)
        self.hub: PubSub = AMemoryPubSub(asyncio.Queue)

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

    def _event(self, event: Union[EventLogType, TaskState], value=None):
        tid = asyncio.current_task().get_name()
        return {'id': tid, 'event': event.value, 'value': value}

    async def start(self, path, monitor_mode):
        """
        Start classifier. If monitor_mode is True, this function never ends and 
        progress bar will stick to 49%

        It will emit event logs via centralized hub, event types are Progress and State.

        It will raise Exception if there is an issue while running, after State chagned to TaskState.Failed

        @TODO: add tests
        """
        logger.info(f"start CG detection: {path=} {monitor_mode=}")
        p = Path(path)

        # path must be a directory
        if not p.exists():
            raise Exception(f'Path not exists: {p}')
        if not p.is_dir():
            raise Exception(f'Path is not directory: {p}')

        try:
            await self.hub.publish(EventTopics.State,
                                   self._event(TaskState.Ongoing))

            # these calls can be blocking, consider run_in_executor
            self.rpc.stopDetector()
            self.rpc.startDetector(path, monitor_mode)

            for i in range(1, 5):
                child_dir = p / str(i)
                child_dir.mkdir(exist_ok=True)
                logger.info(f"created result directory: {child_dir}")

            counter = Counter()
            progress_value = 0

            results = []
            while progress_value < 100:
                batch_end_idx, total_count = self.rpc.getPos()

                # handle empty or error cases
                if total_count == -1:
                    logger.info('waiting for gathering samples')
                    continue
                elif total_count == 0:
                    logger.error(f"sample directory is empty: {p.resolve()}")
                    break

                logger.debug(f'getting detection results')
                results = copy.deepcopy(self.rpc.getResults())
                processed_count = len(results)
                logger.info(f"total processed counts: {processed_count}")

                progress_value = processed_count / total_count * 100.0

                logger.info(
                    f"detection progress: {progress_value}% ({processed_count}/{total_count})"
                )

                await self.hub.publish(
                    EventTopics.Logs,
                    self._event(
                        EventLogType.Progress, {
                            'progress': progress_value,
                            'processed': processed_count,
                            'total': total_count
                        }))

                # wait for another round
                await asyncio.sleep(0.5)

            # 4 kinds of label
            triggered_samples = {k: [] for k in self.label_txt_mappings}

            for item in results:
                filename, label, confidence_level = item

                label = int(label)
                label_txt = None
                try:
                    label_txt = self.label_txt_mappings[label]
                except IndexError:
                    raise IndexError(
                        f'{label=} is invalid. Max label index is {len(self.label_txt_mappings)}'
                    )

                if label == 0:
                    # skip item with label = 0
                    continue

                logger.info(
                    f"found result: {filename=} {label=} {confidence_level=}")

                bname = Path(filename).stem

                if confidence_level >= self.thresholds[label]:
                    counter[f'{label}|{label_txt}'] += 1
                    triggered_samples[label_txt].append({
                        'idx': int(bname),
                        'confidence': confidence_level,
                        'label': label_txt
                    })

                pathd = (p / str(label) / f"{ confidence_level }_{bname}.png")
                paths = p / filename
                shutil.copyfile(paths, pathd)
                logger.debug(f"copy {paths=} to {pathd=}")

            logger.info(
                f"completed CG detection: {counter=}, details={triggered_samples}"
            )

            await self.hub.publish(
                EventTopics.Logs,
                self._event(
                    EventLogType.Results, {
                        'results': triggered_samples,
                        'labelMapping': self.label_txt_mappings
                    }))

        except Exception as e:
            logger.error(f"failed to run detector: {e}")
            await self.hub.publish(EventTopics.State,
                                   self._event(TaskState.Failed))
            # propogate error to caller
            raise e
        finally:
            logger.debug(f'wait 2s before stopping detector')
            await asyncio.sleep(2)
            await self.stop()
            await self.hub.publish(EventTopics.State,
                                   self._event(TaskState.Completed))

    async def stop(self):
        logger.debug('stopping detector')
        if self.debug:
            logger.debug(
                'in debug mode, sleep for 1s, not really stop the detector via RPC'
            )
            await asyncio.sleep(1)
        else:
            self.rpc.stopDetector()
        logger.info(f"stopped detector")
