import asyncio
from pathlib import Path
from wotapi.utils import id_factory

TaskDone = "--END--"


class TaskService:
    async def _run_script(self, path: Path, queue: asyncio.Queue = None):
        for i in range(5):
            await queue.put(i)
            await asyncio.sleep(1)
        await queue.put(TaskDone)

        return

    async def submit(self, action: str, queue: asyncio.Queue = None) -> str:
        tid = id_factory.get()
        task = asyncio.create_task(self._run_script(Path("."), queue))
        return tid
