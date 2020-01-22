from wotapi.services.camera import CameraService
from wotapi.utils import logger
import asyncio
import paco


from aio_pubsub.backends.memory import MemoryPubSub


async def run_hub():
    """
    Testing PubSub
    """
    pubsub = MemoryPubSub()
    # Create subscriber
    subscriber = await pubsub.subscribe("a_chan")

    # Push message
    await pubsub.publish("a_chan", "hello world!")
    await pubsub.publish("a_chan", "hello universe!")
    await pubsub.publish("a_chan", "1")

    # And listening channel
    try:
        async for message in subscriber:
            print(message, flush=True)
    except KeyboardInterrupt:
        print("Finish listening")


async def listen(observable, name):
    """
    Handler for incoming events
    """
    async for item in observable:
        logger.debug(f"{name}: get item {item.keys()!s}")
        if name == "intensity_stream":
            logger.debug(item["stats"])


async def main():
    cs = CameraService()
    info = cs.get_info()
    logger.debug(f"Camera info: {info!s}")
    # Connect w/ the event stream
    # await cs.init_subscribers()
    # Kick off the subscribers
    await paco.gather(
        cs.connect(),
        listen(cs.image_stream, "image_stream"),
        listen(cs.intensity_stream, "intensity_stream"),
    )
    # cmd = {'PICH': 1}
    # cs.cmd_queue.put(cmd)
    # await asyncio.sleep(1)
    # async for item in cs.get_cmd():
    #     logger.debug(item)
