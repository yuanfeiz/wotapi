import asyncio
from pathlib import Path
from wotapi.utils import id_factory, logger
from typing import Mapping

TaskDone = "--END--"


class TaskService:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.running_tasks: Mapping[str, asyncio.Task] = {}

    async def _run_script(
        self, filename: str, queue: asyncio.Queue = None, /, **kwargs
    ):
        try:
            script_path = f"{self.root_path}/{filename}"
            args = ""
            if kwargs.get("__SINGLE"):
                l = kwargs.pop("__SINGLE")
                args = " ".join([str(v) for v in l])
            else:
                args = " ".join([f"--{k}={v}" for k, v in kwargs.items()])

            cmd = f"python -u {script_path} {args}"
            proc = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE
            )
            logger.debug(f"Start executing {cmd}")

            while not proc.stdout.at_eof():
                data = await proc.stdout.readline()
                line = data.decode("utf8").strip()
                logger.debug(f"Read line {line}, put to the queue: {queue}")
                if queue and len(line) > 0:
                    await queue.put(line)

            if queue:
                await queue.put(TaskDone)
            return await proc.wait()
        except asyncio.CancelledError as e:
            logger.debug(
                f"Cancel script executing {script_path}, pid={proc.pid}"
            )
            # Return the CancelledError to terminal the queue
            if queue:
                await queue.put(e)
            proc.terminate()

    async def submit(
        self, action: str, queue: asyncio.Queue = None, /, **kwargs
    ) -> str:
        logger.debug(f"Accept submitted task: {action=}, {kwargs=}")
        tid = id_factory.get()
        filename = f"{action}.py"
        task = asyncio.create_task(self._run_script(filename, queue, **kwargs))
        self.running_tasks[tid] = task
        return tid

    async def cancel(self, tid: str, stop_script_filename="stop"):
        """
        Cancel the running task.

        Return value is the exit value of stop.py script
        """
        try:
            task = self.running_tasks[tid]
        except KeyError:
            raise Exception(f"task {tid} is not running")
        logger.debug(f"Force cancelling task {tid}")
        task.cancel()

        tid = await self.submit(stop_script_filename)
        # Wait for the stop script to finish
        exit_code = await self.running_tasks[tid]
        if exit_code != 0:
            raise Exception(f"unexpected {exit_code=}")
        return exit_code
