from aio_pubsub.backends.memory import MemoryPubSub
import pytest
import asyncio


async def ttest_pubsub():
    pubsub = MemoryPubSub()
    # Create subscriber

    # Push message
    await pubsub.publish("a_chan", "hello world!")

    subscriber = await pubsub.subscribe("a_chan")

    await pubsub.publish("a_chan", "hello universe!")

    # And listening channel
    try:
        async for message in subscriber:
            print(message, flush=True)
    except KeyboardInterrupt:
        print("Finish listening")


async def bar(val):
    await asyncio.sleep(1)
    if val > 3:
        raise Exception("bar")
    else:
        return val


async def foo():
    for i in range(5):
        r = await bar(i)
        yield r


async def main():
    async for i in foo():
        print(i)


if __name__ == "__main__":
    asyncio.run(main())
