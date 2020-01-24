from aiohttp import web
from wotapi.server import setup_app


def create_app():
    return setup_app(web.Application())


if __name__ == "__main__":
    # Kick off the game
    app = create_app()
    web.run_app(app, port=8082)
