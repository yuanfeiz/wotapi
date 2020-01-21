from configparser import ConfigParser
import logging
from shortid import ShortId

# Config
config = ConfigParser()
config.read_dict(
    {
        "camera_rpc": {"host": "localhost", "port": 51235},
        "camera_queue": {
            "host": "localhost",
            "port": 51234,
            "authkey": "wotwot",
            "status_queue_name": "status_queue",
            "cmd_queue_name": "cmd_queue",
        },
    }
)


# Logger
logger = logging.getLogger("wotapi")
sh = logging.StreamHandler()
fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
sh.setFormatter(fmt)
logger.addHandler(sh)
logger.setLevel(logging.DEBUG)


# uuid
id_factory = ShortId()
