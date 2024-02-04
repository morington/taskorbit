import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Callable, Awaitable, Optional, Union

from taskorbit.dispatching.queue import Queue
from taskorbit.models import TaskMessage
from taskorbit.timer import TimerManager

logger = logging.getLogger(__name__)


class BaseHandler(ABC):
    def __init__(self) -> None:
        self._timer_manager = TimerManager()

        self.uuid: Optional[str] = None

        self.execution_timeout: Optional[int] = None
        self.on_execution_timeout: Optional[Callable[[], Awaitable[None]]] = None

        self.close_timeout: Optional[int] = None
        self.on_close: Optional[Callable[[], Awaitable[None]]] = None

    async def _execution(self) -> None:
        if self.on_execution_timeout is not None:
            await self.on_execution_timeout()
        else:
            logger.debug(f"Please wait, the task-{self.uuid} is still in progress...")

    async def _close(self) -> None:
        self._timer_manager.cancel_timers()
        if self.handle_task is not None:
            self.handle_task.cancel()
            if self.on_close is not None:
                self.on_close()
            else:
                logger.debug("Closed!")

    def cancel(self, queue: Queue) -> None:
        self._timer_manager.cancel_timers()
        if self.uuid in queue:
            queue.pop(self.uuid)

    @abstractmethod
    async def handle(self, *args, **kwargs) -> None: ...

    async def __call__(self, queue: Queue, **kwargs) -> None:
        await self._timer_manager.start_timer(self.execution_timeout, self._execution)
        await self._timer_manager.start_timer(self.close_timeout, self._close)
        self.handle_task = asyncio.create_task(self.handle(**kwargs))
        self.handle_task.add_done_callback(lambda future: self.cancel(queue))


class Handler(BaseHandler):
    async def handle(self, *args, **kwargs) -> None:
        raise NotImplementedError


HandlerType = Union[BaseHandler, Handler, Callable[[TaskMessage], Awaitable[None]]]
