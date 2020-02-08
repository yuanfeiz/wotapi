from typing import Any, Counter, Mapping
from wotapi.models import EventLogType
from wotapi.utils import logger
import abc
from json_tricks import dumps, loads


class LogParser(metaclass=abc.ABCMeta):
    """Abstract Parser
    """
    @abc.abstractmethod
    def parse(self, item):
        pass


class SchedulerEventParser(LogParser):
    def __init__(self):
        pass

    def parse(self, item):
        return {**item, 'parser': str(__class__)}


class RunProgressParser(LogParser):
    """
    The task object to parse script output etc.
    """

    mapping = {
        "CT": "concentration",
        "PD": "capturing",
        "IC": "detection",
    }

    def __init__(self):
        # task name -> progress
        self.progress = {}
        self.reset()

    def parse(self, line: str):
        if not line.startswith("STAT"):
            logger.debug(f"Ignore line: {line}")
            return

        c = line[len("STAT:"):]

        if c == "START":
            self.reset()
        elif c == "END":
            self.reset(100)
        else:
            k, v = c.split()
            # Convert progress values to integer
            v = float(v)
            self.progress[self.mapping[k]] = v
        return {
            "event": EventLogType.Progress,
            "value": self.progress,
            'parser': str(__class__)
        }

    def reset(self, pct=0):
        for v in self.mapping.values():
            self.progress[v] = pct


class DetectionMuxLogParser(LogParser):
    """
    A multiplixer for detection service generating logs
    """
    def parse(self, record: Mapping[str, Any]):
        """
        Record is allowed to contain non JSON serializable values,
        it will be handled by json-tricks which acts as the default encoder
        defined in socket_io.py
        """
        logger.debug(f'parse {record=}')
        return record