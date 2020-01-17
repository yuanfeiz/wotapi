from configparser import ConfigParser

config = ConfigParser()
config.read_dict(
    {
        "camera_rpc": {"host": "localhost", "port": 51235},
        "camera_queue": {
            "host": "localhost",
            "port": 51234,
            "authkey": "wotwot",
            "status_queue_name": "status_queue",
            "command_queue_name": "cmd_queue",
        },
    }
)
