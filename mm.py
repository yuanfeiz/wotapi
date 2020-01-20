import mmap
import simplejson as json
import time
import asyncio
import paco
import aiofiles

path = "/Users/yuanfei/Projects/siu/wot/wot-core/su/dfppmgui.json"


async def update_file_per_secs():
    rets = []
    while True:
        s = time.monotonic()
        rets.append(s)
        with open(path, "w+") as f:
            json.dump({"times": rets}, f)
            print(f"Server: updated: {s}")
        await asyncio.sleep(2)


async def read_status():
    async with aiofiles.open(path, "r+") as f:
        content = await f.readline()
        status_report = json.loads(content)
        print(json.dumps(status_report, sort_keys=True, indent=2))


async def read_file_per_secs():
    while True:
        await read_status()
        await asyncio.sleep(1)


if __name__ == "__main__":
    # paco.run(paco.gather(update_file_per_secs(), read_file_per_secs()))
    # paco.run(read_status())
    c = C(1)
    s = json.dumps(asdict(c))
    print(s)

