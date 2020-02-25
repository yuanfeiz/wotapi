from wotapi.libs.json_helpers import json_response, loads
from aiohttp import MultipartWriter, web
from ..utils import logger
from ..services import CameraService, image

routes = web.RouteTableDef()


async def write_new_parts(data, boundary, response):
    with MultipartWriter("image/jpeg", boundary=boundary) as mpwriter:

        mpwriter.append(data, {"Content-Type": "image/jpeg"})
        # mpwriter.append(byte_im, {"Content-Type": "image/jpeg"})
        await mpwriter.write(response, close_boundary=False)
        logger.debug(f"Append response")
    await response.drain()


@routes.get(r"/feeds/capturing/{img_type}")
async def timg_feed(request) -> web.StreamResponse:
    my_boundary = "some-boundary"

    response = web.StreamResponse(
        status=200,
        reason="OK",
        headers={
            "Content-Type":
            "multipart/x-mixed-replace;boundary=--%s" % my_boundary
        },
    )
    await response.prepare(request)

    csrv: CameraService = request.app["camera_service"]
    img_stream = await csrv.hub.subscribe("image")
    img_type = request.match_info.get("img_type").upper()
    logger.debug(f"Subscribe to image stream {img_type=}")

    for i in range(2):
        await write_new_parts(image.img_to_bytes(image.blank_image()),
                              my_boundary, response)

    try:
        async for item in img_stream:
            if img_type not in item:
                logger.debug(f"Skip image item: {img_type=} {item.keys()}")
                continue

            img = image.frombuffer(item[img_type])
            await write_new_parts(image.img_to_bytes(img), my_boundary,
                                  response)
        await response.write_eof()
    except ConnectionResetError:
        logger.warning(f"Ignored premature client disconnection")
    finally:
        logger.debug("Finished streaming")
        return response


@routes.get('/camera')
async def get_camera_info(request):
    csrv: CameraService = request.app["camera_service"]
    info = csrv.get_info()
    return json_response({'cameraInfo': info})