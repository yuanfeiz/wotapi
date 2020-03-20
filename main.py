from wotapi.utils import logger
import asyncio

async def foo():
    cnt = 0    
    while True:
        logger.info(f'foo: {cnt}')
        cnt += 1
        await asyncio.sleep(1)
        
async def bar():
    await asyncio.sleep(3)
    logger.info(f'bar: done')

async def main():
    done, pending = await asyncio.wait([foo(), bar()], return_when=asyncio.FIRST_COMPLETED)
    logger.info(f'{done}, {pending}')

asyncio.run(main())
