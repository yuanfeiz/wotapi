import socketio

socket_io = socketio.AsyncServer(logger=True, cors_allowed_origins="*")
