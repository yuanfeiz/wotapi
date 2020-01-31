from aiohttp import web
from wotapi.server import setup_app
from configparser import ConfigParser


def create_app():
    config = ConfigParser()
    config.read("config.prod.ini")
    return setup_app(web.Application(), config)


if __name__ == "__main__":
    # Kick off the game
    app = create_app()
    web.run_app(app, port=8085)
