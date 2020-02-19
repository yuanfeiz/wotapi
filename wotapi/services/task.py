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
        self, filename: str, queue: asyncio.Queue = None, /, **script_argv
    ):
        script_path = f"{self.root_path}/{filename}"

        # process script arguments
        args = ""
        if "_" in script_argv:
            vs = script_argv.pop("_")
            args = " ".join([str(v) for v in vs])

        args = " ".join([f"--{k}={v}" for k, v in script_argv.items()])

        cmd = f"python -u {script_path} {args}"

        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        logger.info(f"Executing --- ({proc.pid}) `$ {cmd}`")

        try:
            while not proc.stdout.at_eof():
                data = await proc.stdout.readline()
                line = data.decode("utf8").strip()

                if len(line) == 0:
                    continue

                logger.info(f"({filename}) >>> {line}")

                if queue:
                    await queue.put(line)
            exit_code = await proc.wait()
            logger.info(f'Finished ---- ({proc.pid}) `$ {cmd}` {exit_code=}')

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
            proc.terminate()
            raise e

    async def create_script_task(
        self, action: str, queue: asyncio.Queue = None, **kwargs  # noqa
    ) -> str:
        tid = id_factory.get()
        logger.debug(f"Accept submitted task({tid}): {action=}, {kwargs=}")
        # action can contains a prefix identifies its group
        filename = f"{action.split('.')[-1]}.py"
        self.create_task(self._run_script(filename, queue, **kwargs), tid)
        return tid

    async def run_script(self, script_filename: str, *script_argv):
        """
        Run script, wait until complete
        """
        tid = await self.create_script_task(script_filename, None, _=script_argv)
        # Wait for the stop script to finish
        exit_code = await self.running_tasks[tid]
        if exit_code != 0:
            raise Exception(f"unexpected {exit_code=}")
        return exit_code

    def create_task(self, coro, tid: str = None) -> asyncio.Task:
        """
        Create task with uuid and keep track of it in the task registry
        """
        if tid is None:
            tid = id_factory.get()
        task = asyncio.create_task(coro, name=tid)
        self.running_tasks[tid] = task
        return task

    def get(self, tid: str) -> asyncio.Task:
        return self.running_tasks[tid]

    def clear(self, tid: str):
        logger.warning(f'clean up task: {tid}')
        del self.running_tasks[tid]

