import asyncio
from pathlib import Path
from wotapi.utils import id_factory, logger
import sys

TaskDone = "--END--"


class TaskService:
    def __init__(self, root_path: Path):
        self.root_path = root_path

    async def _run_script(self, filename: str, queue: asyncio.Queue = None):
        try:
            script_path = f'{self.root_path}/{filename}'
            proc = await asyncio.create_subprocess_shell(f'python -u {script_path}', stdout=asyncio.subprocess.PIPE)
            logger.debug(f"Start executing {script_path}")

            while not proc.stdout.at_eof():
                data = await proc.stdout.readline()
                line = data.decode("utf8").strip()
                logger.debug(f"Read line {line}, put to the queue")
                await queue.put(line)

            await queue.put(TaskDone)
            return await proc.wait()
        except asyncio.CancelledError:
            proc.terminate()


    async def submit(self, action: str, queue: asyncio.Queue = None) -> str:
        tid = id_factory.get()
        filename = f'{action}.py'
        task = asyncio.create_task(self._run_script(filename, queue))
        return tid
