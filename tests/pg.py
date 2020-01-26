import asyncio
import time

import sys

print(sys.executable)


async def vanilla_run_once():
    print(time.monotonic())
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "resources/mock_auto_mode.py", stdout=asyncio.subprocess.PIPE
    )
    while not proc.stdout.at_eof():
        print(time.monotonic())
        data = await proc.stdout.readline()
        line = data.decode("utf8").strip()
        print(line, flush=True)
        await asyncio.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(vanilla_run_once())
