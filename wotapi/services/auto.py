import asyncio
import random
from ..utils import id_factory

class AutoService:

    def __init__(self):
        pass


    async def schedule_run_once(self) -> str: 
        return id_factory.generate()

    async def schedule_run_period(self) -> str: 
        return id_factory.generate()

    async def schedule_run_multiple(self) -> str: 
        return id_factory.generate()