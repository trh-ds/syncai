import asyncio
from collections.abc import AsyncGenerator

_event_queue: asyncio.Queue[dict] = asyncio.Queue()


async def emit(event: dict):
    await _event_queue.put(event)


async def subscribe() -> AsyncGenerator[dict, None]:
    while True:
        event = await _event_queue.get()
        yield event
