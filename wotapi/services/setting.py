from pathlib import Path
import json
import asyncio
from wotapi.utils import logger


class SettingService:
    """
    Read and update settings that stores at path
    """

    def __init__(self, path: Path):
        if isinstance(path, str):
            path = Path(path)
        self.path = path
        logger.debug(
            f"Initialized SettingService with config path: {self.path}"
        )
        # The lock currently doesn't work as load and dump
        # are both blocking operation
        self.lock = asyncio.Lock()

    async def get(self):
        """
        If blocking read is ok, then go with it. Otherwise we'll change to aiofiles
        """
        async with self.lock:
            with self.path.open("r+") as f:
                content = json.load(f)
                logger.debug(f"Get config: {content}")
                return content

    async def update(self, o: dict):
        async with self.lock:
            with self.path.open("w+") as f:
                json.dump(o, f, indent=2)
                logger.debug(f"Updated config: {o}")