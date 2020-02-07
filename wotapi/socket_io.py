import socketio
from wotapi.libs import json_helpers

socket_io = socketio.AsyncServer(logger=True,
                                 cors_allowed_origins="*",
                                 json=json_helpers)
