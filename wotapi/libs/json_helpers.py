from functools import partial
import json_tricks
from aiohttp import web
from enum import Enum
from rpyc.core.netref import _builtin_types
from wotapi.utils import logger


def enum_instance_encode(obj):
    """
    `obj.value` is all we need
    """
    if not isinstance(obj, Enum):
        return obj
    else:
        return obj.value


def rpyc_instance_encode(obj, is_changed=None, fallback_value=None):
    if is_changed:
        return obj

    if isinstance(obj, dict):
        return {k: obj[k] for k in obj}
    elif isinstance(obj, list):
        return [k for k in obj]
    else:
        return obj


loads = json_tricks.loads
dumps = partial(json_tricks.dumps,
                obj_encoders=[
                    enum_instance_encode,
                ],
                primitives=True,
                fallback_encoders=[rpyc_instance_encode])
json_response = partial(web.json_response, dumps=dumps)