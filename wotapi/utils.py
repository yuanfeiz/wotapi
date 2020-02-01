import logging
from shortid import ShortId


# Logger
logger = logging.getLogger("wotapi")
sh = logging.StreamHandler()
fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
sh.setFormatter(fmt)
logger.addHandler(sh)
logger.setLevel(logging.INFO)


logging.getLogger("socketio.server").setLevel(logging.ERROR)
# uuid
class IdFactory:
    def __init__(self):
        self.f = ShortId()

    def get(self):
        return self.f.generate()


id_factory = IdFactory()
