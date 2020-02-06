import asyncio
from pathlib import Path
from wotapi.utils import id_factory, logger
from typing import Mapping, MutableMapping
import io

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
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        logger.info(f"Executing --- {cmd}({proc.pid})")

        try:
            while not proc.stdout.at_eof():
                data = await proc.stdout.readline()
                line = data.decode("utf8").strip()
                logger.info(f"({filename}) >>> {line}")
                if queue and len(line) > 0:
                    await queue.put(line)
            exit_code = await proc.wait()
            logger.info(f'Finished ---- {cmd}({proc.pid}) {exit_code=}')

            # raise exception if exit_code is not 0
            if exit_code != 0:
                msg = 'Execution abort! Reason: '

                # all stderr msg is buffered
                while not proc.stderr.at_eof():
                    data = await proc.stderr.readline()
                    line = data.decode("utf8").strip()
                    logger.error(f"({filename}) >>> {line}")
                    msg += line
                raise Exception(msg)
            
            return exit_code
        except asyncio.CancelledError as e:
            logger.warning(
                f"Cancel process {cmd}({proc.pid})"
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

    def create_task(self, coro, tid: str = None) -> asyncio.Task:
        """
        Create task with uuid and keep track of it in the task registry
        """
        if tid is None:
            tid = id_factory.get()
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

    def get(self, tid: str) -> asyncio.Task:
        return self.running_tasks[tid]

