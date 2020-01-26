from wotapi.utils import logger


class AutoflowParser:
    """
    The task object to parse script output etc.
    """

    mapping = {
        "CT": "concentration",
        "PD": "particles_capturing",
        "IC": "particles_detection",
    }

    def __init__(self):
        # task name -> progress
        self.progress = {}
        self.reset()

    def parse(self, line: str):
        if not line.startswith("STAT"):
            logger.debug(f"Ignore line: {line}")
            return

        c = line[len("STAT:") :]

        if c == "START":
            self.reset()
        elif c == "END":
            self.reset(100)
        else:
            k, v = c.split()
            # Convert progress values to integer
            v = int(v)
            self.progress[self.mapping[k]] = v
        return {"event": "progress", "progress": self.progress}

    def reset(self, pct=0):
        for v in self.mapping.values():
            self.progress[v] = pct
