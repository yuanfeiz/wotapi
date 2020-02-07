from functools import partial
import json_tricks
from aiohttp import web
from enum import Enum


def enum_instance_encode(obj):
    """
    `obj.value` is all we need
    """
    if not isinstance(obj, Enum):
        return obj
    else:
        return obj.value


loads = json_tricks.loads
dumps = partial(json_tricks.dumps,
                obj_encoders=[enum_instance_encode],
                primitives=True)
json_response = partial(web.json_response, dumps=dumps)