import abc
import asyncio
import logging
from typing import Type, Any, Callable
from functools import partial

from taskorbit.dispatching.handler import HandlerType
from taskorbit.dispatching.queue import Queue
from taskorbit.dispatching.router import Router
from taskorbit.enums import Commands, TaskStatus
from taskorbit.middlewares.manager import MiddlewareManager
from taskorbit.models import ServiceMessage, Metadata, Message
from taskorbit.utils import get_list_parameters

logger = logging.getLogger(__name__)


class Dispatcher(Router):
    def __init__(self, max_queue_size: int) -> None:
        super().__init__()
        self.middleware = MiddlewareManager()
        self.inner_middleware = MiddlewareManager()
        self.queue: Queue[str, asyncio.Task] = Queue(max_queue_size)
        self.context_data: dict = {}

    def __setitem__(self, key, value):
        self.context_data[key] = value

    async def _service_processing(self, metadata: ServiceMessage) -> None:
        logger.debug(f"Getting service messages: {metadata.command}")
        if metadata.command == Commands.GET_STATUS:
            status: TaskStatus = self.queue.get_status_task(metadata.uuid)
            logger.debug(f"Task-{metadata.uuid} STATUS: {status}")
        elif metadata.command == Commands.CLOSING:
            if metadata.uuid in self.queue:
                self.queue[metadata.uuid].cancel()
                logger.debug(f"The task-{metadata.uuid} was forcibly completed")
            else:
                logger.warning(f"Failed to close the task-{metadata.uuid}, there is no such task in the queue")

    def __cb_close_task(self, future) -> None:
        name = future.get_name()
        self.queue.pop(name)
        logger.debug(f"The task-{name} has been removed from the queue")

    async def listen(self, metadata: Metadata) -> None:
        if isinstance(metadata, ServiceMessage):
            _ = asyncio.create_task(self._service_processing(metadata))
        elif isinstance(metadata, Message):
            try:
                task = asyncio.create_task(self._metadata_processing(metadata), name=metadata.uuid)
                task.add_done_callback(self.__cb_close_task)
                self.queue[metadata.uuid] = task
            except Exception as e:
                logger.error(e.args[0])

    async def _metadata_processing(self, metadata: Metadata) -> None:
        data = self.context_data.copy()

        try:
            call_processing: partial = await self.middleware.middleware_processing(handler=self._message_processing, metadata=metadata)
            await call_processing(metadata=metadata, data=data)
        except Exception as e:
            logger.error(f"{e.args[0]}")

    async def _message_processing(self, metadata: Message, data: dict[str, Any]) -> Any:
        handler: Type[HandlerType] = await self.find_handler(metadata=metadata, data=data)

        async def _handler_processing(metadata: Message, data: dict[str, Any]) -> Any:
            nonlocal handler
            if isinstance(handler, abc.ABCMeta):
                handler = handler(**get_list_parameters(handler.__init__, metadata=metadata, data=data))

            fields_cls: dict = get_list_parameters(handler.__call__, metadata=metadata, data=data)
            fields_handle: dict = get_list_parameters(handler.handle, metadata=metadata, data=data, is_handler=True)
            fields_execution_callback: dict = get_list_parameters(handler.on_execution_timeout, metadata=metadata, data=data, is_handler=True)
            fields_close_callback: dict = get_list_parameters(handler.on_close, metadata=metadata, data=data, is_handler=True)

            return await handler(**{
                    **fields_cls, **fields_handle,
                    'fields_execution_callback': fields_execution_callback,
                    'fields_close_callback': fields_close_callback
            })

        call_processing: partial | Callable = await self.inner_middleware.middleware_processing(handler=_handler_processing, metadata=metadata)

        try:
            return await call_processing(metadata=metadata, data=data)
        except Exception as e:
            logger.error(f"{e.args[0]}")
