import time
from multiprocessing.managers import BaseManager

import numpy as np
import rpyc


class Camera:
    """
    Camera of the detector, control via RPC
    """
    def __init__(self, ip="127.0.0.1", port=51235):
        self.rpc = rpyc.connect(ip, port).root

    def get_info(self):
        return self.rpc.getCamera()


class DetectionQueueManager(BaseManager):
    pass


def bytes_to_image(data, camera_height, camera_width):
    obj = np.frombuffer(data, dtype=np.uint8)
    obj = obj.reshape((camera_height, camera_width))
    return obj


def test_status_queue():
    DetectionQueueManager.register("status_queue")
    DetectionQueueManager.register("cmd_queue")
    queue_mgt = DetectionQueueManager(("127.0.0.1", 51234), authkey=b"wotwot")

    queue_mgt.connect()

    status_queue = queue_mgt.status_queue()
    cmd_queue = queue_mgt.cmd_queue()

    srv = ImageService()

    c = Camera()
    camera_info = c.get_info()
    h, w = camera_info["H"], camera_info["W"]
    while True:
        s = status_queue.get(timeout=10)
        print(s.keys())
        millisecs = int(time.time() * 1000)
        if "CIMG" in s:
            img = srv.frombuffer(s["CIMG"], h, w)
            with open(f"assets/cimg-{millisecs}.png", "wb+") as f:
                img.save(f, format="png")
        elif "TIMG" in s:
            img = srv.frombuffer(s["TIMG"], h, w)
            with open(f"assets/timg-{millisecs}.png", "wb+") as f:
                img.save(f, format="png")

        time.sleep(0.1)


def test_detector():
    c = Camera()
    print(c.get_info())


if __name__ == "__main__":
    test_detector()
