from aio_pubsub.backends.memory import MemoryPubSub, MemorySubscriber

class AMemorySubscriber(MemorySubscriber):
    async def __anext__(self):
        return await self.messages.get()


class AMemoryPubSub(MemoryPubSub):
    async def subscribe(self, channel: str):
        subscriber = AMemorySubscriber(self.queue_factory)
        self.subscribers[channel].add(subscriber)
        return subscriber