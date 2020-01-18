from pathlib import Path
import logging
import rpyc

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


class DetectorService:
    """
    This service relie on a running cgdetector.x64
    """

    def __init__(self, ip="localhost", port=51237):
        config = {"allow_pickle": True}
        self.rpc = rpyc.connect(ip, port, config).root

    def get_info(self):
        return self.rpc.getCamera()


if __name__ == "__main__":
    sample_path = Path("/Users/yuanfei/Projects/siu/wot/wot-app/data/triggered_img.png")

    ds = DetectorService()

    ds.rpc.stopDetector()
    ds.rpc.startDetector(str(sample_path), True)

    while True:
        logging.info(f"{dc.rpc.getPos()=}")
        logging.info(f"{ds.rpc.getResults()=}")
        time.sleep(0.5)