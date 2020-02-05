from wotapi.models import EventLogType
from wotapi.utils import logger
import abc


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
        return item


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
            v = int(v)
            self.progress[self.mapping[k]] = v
        return {"event": EventLogType.Progress, "value": self.progress}

    def reset(self, pct=0):
        for v in self.mapping.values():
            self.progress[v] = pct
