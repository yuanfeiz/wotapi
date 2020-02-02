import logging
import coloredlogs
from shortid import ShortId


# Logger
coloredlogs.install()
logger = logging.getLogger("wotapi")
# sh = logging.StreamHandler()
# fmt_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# fmt = logging.Formatter(fmt_str)
# sh.setFormatter(fmt)
# logger.addHandler(sh)
logger.setLevel(logging.INFO)

logging.getLogger("engineio.server").setLevel(logging.WARNING)


# uuid
class IdFactory:
    def __init__(self):
        self.f = ShortId()

    def get(self):
        return self.f.generate()


id_factory = IdFactory()
