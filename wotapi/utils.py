import logging
# from logging.handlers import TimedRotatingFileHandler
from shortid import ShortId
from pathlib import Path
from loguru import logger
'''
# Logger
logger = logging.getLogger("wotapi")

# StreamHandler
sh = logging.StreamHandler()
fmt_str = "%(asctime)s | %(name)s [%(levelname)s] - %(message)s"
%d{yyyy-MM-dd} | %d{HH:mm:ss.SSS} | %thread | %5p | %logger{25} | %12(ID: %8mdc{id}) | %m%n
fmt = logging.Formatter(fmt_str)
sh.setFormatter(fmt)
sh.setLevel(logging.INFO)
logger.addHandler(sh)

# FileHandler
p = Path('/tmp/logs/wotapi.log')
p.parent.mkdir(parents=True, exist_ok=True)
fh = TimedRotatingFileHandler(p)
fh.setFormatter(fmt)
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)

logger.setLevel(logging.DEBUG)
'''

logging.getLogger("engineio.server").setLevel(logging.WARNING)
logging.getLogger("socketio.server").setLevel(logging.WARNING)


# uuid
class IdFactory:
    def __init__(self):
        self.f = ShortId()

    def get(self):
        return self.f.generate()


id_factory = IdFactory()
