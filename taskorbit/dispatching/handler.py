import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Callable, Awaitable, Optional, Union

from taskorbit.timer import TimerManager

logger = logging.getLogger(__name__)


class BaseHandler(ABC):
    def __init__(self) -> None:
        self.__task = None
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

    async def _close(self, *args, **kwargs) -> None:
        logger.debug("The timeout has expired and the task is being closed...")
        if self.__task is not None:
            self.__task.cancel()
        else:
            logger.warning("Closing via timeout was incorrect. The task does not exist!")
            self.cancel(...)

    def cancel(self, _) -> None:
        self._timer_manager.cancel_timers()
        logger.debug("Cancelled")

    @abstractmethod
    async def handle(self, *args, **kwargs) -> None: ...

    async def __call__(self, **kwargs) -> None:
        try:
            self.__task = asyncio.create_task(self.handle(**kwargs))
            self.__task.add_done_callback(self.cancel)

            await self._timer_manager.start_timer(self.execution_timeout, self._execution)
            await self._timer_manager.start_timer(self.close_timeout, self._close)
            await self.__task
        except Exception as e:
            logger.debug(f"An error occurred: {e.args[0]}")


class Handler(BaseHandler):
    async def handle(self, *args, **kwargs) -> None:
        raise NotImplementedError


HandlerType = Union[BaseHandler, Handler, Callable]
