from aiohttp import web
from wotapi.services import SettingService, CameraService
from ..libs.json_helpers import json_response
from ..utils import logger
import asyncio

routes = web.RouteTableDef()


@routes.get("/settings")
async def get_settings(request):
    setting_service: SettingService = request.app["setting_service"]
    return json_response({
        "settings": await setting_service.get(),
        "meta": {
            "path": str(setting_service.path)
        },
    })


@routes.put("/settings")
async def update_settings(request):
    payload = await request.json()
    new_settings = payload["settings"]

    # the update key can be none for mirror changes that
    # doesn't have side effect
    updated_key = payload.get("key")
    logger.debug(f'settings[{updated_key}] is updated')

    # Update the config file
    setting_service: SettingService = request.app["setting_service"]
    await setting_service.update(new_settings)

    camera_service: CameraService = request.app["camera_service"]
    if updated_key == "imaging":
        # Request detector to update its parameters
        params = new_settings["imaging"]
        await camera_service.update_intensity_levels(params['low'],
                                                     params['high'])
    elif updated_key == "camera":
        await asyncio.gather(
            camera_service.update_camera_exp(
                new_settings['camera']['exposure']),
            camera_service.update_camera_gain(new_settings['camera']['gain']))

    return json_response({"status": "ok", "settings": new_settings})