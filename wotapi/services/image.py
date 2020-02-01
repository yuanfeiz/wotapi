import numpy as np
from wotapi.utils import logger
from PIL import Image, ImageDraw
import time
import io


def frombuffer(buffer, h: int = 488, w: int = 648):
    logger.debug(f"processing image {h=} {w=}")
    obj = np.frombuffer(buffer, dtype=np.uint8)
    obj = obj.reshape((h, w))
    img = Image.fromarray(obj)

    ImageDraw.Draw(img).text((0, 0), f"WOT - SIU: {time.time()=}", 128)
    return img


def blank_image(H: int = 488, W: int = 648):
    img = Image.new("L", (W, H))
    msg = "LOADING..."
    draw = ImageDraw.Draw(img)
    w, h = draw.textsize(msg)
    draw.text(((W - w) / 2, (H - h) / 2), msg, 128)
    return img


def img_to_bytes(img: Image.Image):
    buf = io.BytesIO()
    img.save(buf, "JPEG")
    return buf.getvalue()
