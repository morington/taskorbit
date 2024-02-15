import asyncio
import inspect
import logging
from abc import ABC, abstractmethod
from types import NoneType
from typing import Callable, Awaitable, Optional, Union, Any

from taskorbit.timer import TimerManager

logger = logging.getLogger(__name__)


class BaseHandler(ABC):
    """
    The base class for all handlers.
    In a project, handlers can act as both functions and classes. But in the end, they are all brought to the class.

    Attributes:
        name (str): The name of the handler for logging.
        uuid (str): The uuid of the task.
        execution_timeout (int): Timeout, after the time expires, performs a callback transmitted to the on_execution_cb or standard with logging.
        on_execution_cb (Callable[[...], Awaitable[None]]): Callback to execute the logic of waiting for a task
        close_timeout (int): Timeout, after the time expires, the task is terminated by the on_close_cb or standard with logging, after the function is
            executed, the task is terminated
        on_close_cb (Callable[[...], Awaitable[None]]): A callback that runs when you want to interrupt a task when a timeout expires
    """
    def __init__(self) -> None:
        self.name = "unknown"

        self.__task = None
        self._timer_manager = TimerManager()

        self.uuid: Optional[str] = None

        self.execution_timeout: Optional[int] = None
        self.on_execution_cb: Optional[Callable[[...], Awaitable[None]]] = None

        self.close_timeout: Optional[int] = None
        self.on_close_cb: Optional[Callable[[...], Awaitable[None]]] = None

        if (
            not isinstance(self.on_execution_cb, Callable | NoneType) or
            not isinstance(self.on_close_cb, Callable | NoneType) or
            inspect.isclass(self.on_execution_cb) or
            inspect.isclass(self.on_close_cb)
        ):
            raise TypeError("The callback must be either a function or NoneType")

    def __str__(self) -> str:
        return f"<Handler:{self.name}>"

    def __repr__(self) -> str:
        return self.__str__()

    async def _execution(self, **kwargs) -> None:
        """Callback execution process for wait timeout"""
        if self.on_execution_cb is not None:
            await self.on_execution_cb(**kwargs)
        else:
            logger.debug(f"Please wait, the task-{self.uuid} is still in progress...")

    async def _close(self, **kwargs) -> None:
        """The process of executing a callback for a program timeout to close at timeout"""
        if self.on_close_cb is not None:
            await self.on_close_cb(**kwargs)

        logger.debug("The timeout has expired and the task is being closed...")
        if self.__task is not None:
            self.__task.cancel()
        else:
            logger.warning("Closing via timeout was incorrect. The task does not exist!")
            self.cancel(...)

    def cancel(self, _) -> None:
        """Executing a function when a task completes"""
        self._timer_manager.cancel_timers()
        logger.debug("Cancelled")

    @abstractmethod
    async def handle(self, *args, **kwargs) -> None:
        """
        The main function of the handler. You have to write your logic here.


        Args:
            *args: The arguments of the handler.
            **kwargs: The keyword arguments of the handler.
        """
        ...

    async def __call__(self, fields_execution_callback: dict[str, Any], fields_close_callback: dict[str, Any], **kwargs) -> None:
        """
        Handler execution process

        Args:
            fields_execution_callback (dict[str, Any]): kwargs for callback waiting
            fields_close_callback (dict[str, Any]): kwargs for callback close
            **kwargs: The arguments of the handler.
        """
        self.__task = asyncio.create_task(self.handle(**kwargs))
        self.__task.add_done_callback(self.cancel)

        await self._timer_manager.start_timer(self.execution_timeout, self._execution, **fields_execution_callback)
        await self._timer_manager.start_timer(self.close_timeout, self._close, **fields_close_callback)
        await self.__task


class Handler(BaseHandler):
    """A variant of the handler wrapper for casting a function to a class."""
    async def handle(self, *args, **kwargs) -> None:
        raise NotImplementedError


HandlerType = Union[BaseHandler, Handler, Callable]
