"""
HTTP endpoints
"""

from aiohttp import web

from .settings import routes as settings_routes
from .automode import routes as automode_routes
from .concentration import routes as concentration_routes
from .images import routes as images_routes
from .capturing import routes as capturing_routes
from .detection import routes as detection_routes
from .task import routes as task_routes

from ..libs.json_helpers import json_response

routes = web.RouteTableDef()


@routes.get("/status")
async def status(request):
    return json_response({"status": "ok"})


all_routes = [
    *routes, *settings_routes, *automode_routes, *concentration_routes,
    *images_routes, *capturing_routes, *detection_routes, *task_routes
]
