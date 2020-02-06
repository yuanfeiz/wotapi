import socketio
import json_tricks

socket_io = socketio.AsyncServer(logger=True,
                                 cors_allowed_origins="*",
                                 json=json_tricks)
