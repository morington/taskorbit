import asyncio
from logging import getLogger
from typing import Optional, Callable, Awaitable


logger = getLogger(__name__)


class TimerManager:
    def __init__(self):
        self.timers: list[asyncio.Task] = []

    async def start_timer(self, timeout: Optional[int], callback: Callable[[...], Awaitable[None]], **kwargs) -> Optional[asyncio.Task]:
        async def timer() -> None:
            await asyncio.sleep(timeout)
            await callback(**kwargs)

        if timeout is not None:
            task = asyncio.create_task(timer())
            self.timers.append(task)
            return task

    def cancel_timers(self, *args):
        for timer in self.timers:
            timer.cancel()
        self.timers.clear()
        logger.debug(f"All timers canceled")
