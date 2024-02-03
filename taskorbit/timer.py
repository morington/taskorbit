import asyncio
from typing import Optional, Callable, Awaitable


class TimerManager:
    def __init__(self):
        self.timers: list[asyncio.Task] = []

    async def start_timer(
        self, timeout: Optional[int], callback: Callable[[], Awaitable[None]]
    ) -> Optional[asyncio.Task]:
        async def timer() -> None:
            await asyncio.sleep(timeout)
            await callback()

        if timeout is not None:
            task = asyncio.create_task(timer())
            self.timers.append(task)
            return task

    def cancel_timers(self, *args):
        print("Closing timers")
        for timer in self.timers:
            timer.cancel()
        self.timers.clear()
