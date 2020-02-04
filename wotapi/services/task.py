import asyncio
from pathlib import Path
from wotapi.utils import id_factory, logger
from typing import Mapping, MutableMapping

TaskDone = "--END--"


class TaskService:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.running_tasks: MutableMapping[str, asyncio.Task] = {}

    async def _run_script(
        self, filename: str, queue: asyncio.Queue = None, /, **kwargs
    ):
        script_path = f"{self.root_path}/{filename}"
        args = ""
        if kwargs.get("__SINGLE"):
            vs = kwargs.pop("__SINGLE")
            args = " ".join([str(v) for v in vs])
        else:
            args = " ".join([f"--{k}={v}" for k, v in kwargs.items()])

        cmd = f"python -u {script_path} {args}"

        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE
        )
        logger.info(f"Start executing {cmd}")

        try:
            while not proc.stdout.at_eof():
                data = await proc.stdout.readline()
                line = data.decode("utf8").strip()
                logger.info(f"Read line {line}, put to the queue: {queue}")
                if queue and len(line) > 0:
                    await queue.put(line)

            if queue:
                await queue.put(TaskDone)
            return await proc.wait()
        except asyncio.CancelledError as e:
            logger.warning(
                f"Cancel script executing {script_path}, pid={proc.pid}"
            )
            # Return the CancelledError to terminal the queue
            if queue:
                await queue.put(e)
            proc.terminate()
            raise e

    async def submit(
        self, action: str, queue: asyncio.Queue = None, /, **kwargs  # noqa
    ) -> str:
        tid = id_factory.get()
        logger.debug(f"Accept submitted task({tid}): {action=}, {kwargs=}")
        filename = f"{action}.py"
        self.create_task(self._run_script(filename, queue, **kwargs), tid)
        return tid

    def create_task(self, coro, tid: str) -> asyncio.Task:
        task = asyncio.create_task(coro, name=tid)
        self.running_tasks[tid] = task
        return task

    async def cancel(self, tid: str, stop_script_filename="stop"):
        """
        Cancel the running task.

        Return value is the exit value of stop.py script
        """
        try:
            task = self.running_tasks[tid]
            logger.debug(f"Force cancelling task {tid}")
            task.cancel()
        except KeyError:
            raise Exception(f"task {tid} is not running")

        tid = await self.submit(stop_script_filename)
        # Wait for the stop script to finish
        exit_code = await self.running_tasks[tid]
        if exit_code != 0:
            raise Exception(f"unexpected {exit_code=}")
        return exit_code

