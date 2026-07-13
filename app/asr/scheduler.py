import asyncio
from collections.abc import Awaitable, Callable
from app.core.config import Settings


class StreamingScheduler:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._running = False
        self._tasks: set[asyncio.Task] = set()

    async def start(self) -> None:
        self._running = True

    async def stop(self) -> None:
        self._running = False
        for task in list(self._tasks):
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    def schedule(self, coro_factory: Callable[[], Awaitable[None]]) -> None:
        if not self._running:
            return
        task = asyncio.create_task(coro_factory())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
