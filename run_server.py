from aiohttp import web
from wotapi.server import setup_app
from configparser import ConfigParser
import os
import os.path

def create_app():
    env = os.getenv("WOT_ENV", default="dev")
    config = ConfigParser()
    config.read(f"config.{env}.ini")
    return setup_app(web.Application(), config)


if __name__ == "__main__":

    exepath = os.path.dirname(os.path.realpath(__file__))
    print(exepath)
    os.chdir(exepath)
    # Kick off the game
    app = create_app()
    web.run_app(app, port=8085)
