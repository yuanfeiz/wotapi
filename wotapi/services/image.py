import numpy as np
from wotapi.utils import logger
from PIL import Image, ImageDraw
import time


def frombuffer(buffer, h: int = 488, w: int = 648):
    logger.debug(f"processing image {h=} {w=}")
    obj = np.frombuffer(buffer, dtype=np.uint8)
    obj = obj.reshape((h, w))
    img = Image.fromarray(obj)

    ImageDraw.Draw(img).text((0, 0), f"WOT - SIU: {time.time()=}", 128)
    return img
