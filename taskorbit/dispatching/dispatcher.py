import _asyncio
import abc
import asyncio
import logging
from typing import Type, Any, Callable
from functools import partial

from taskorbit.dispatching.handler import HandlerType
from taskorbit.dispatching.pool import Pool
from taskorbit.dispatching.router import Router, find_handler
from taskorbit.enums import Commands, TaskStatus
from taskorbit.middlewares.manager import MiddlewareManager
from taskorbit.models import ServiceMessage, Metadata, Message
from taskorbit.utils import get_list_parameters

logger = logging.getLogger(__name__)


class Dispatcher(Router):
    """
    The Dispatcher is a class that is responsible for dispatching messages to the appropriate handler.
    It provides filtering data, middleware, and also searches for handlers on routers.

    The dispatcher has 'stream_data' which is passed along with the message to the middleware, filters and handlers.

    You can enter data into it as follows:

        dp = Dispatcher(max_pool_size=10)

        dp['name']: str = 'John'

    Args:
        max_pool_size (int): The maximum number of tasks that can be in the queue at the same time.
    """
    def __init__(self, max_pool_size: int) -> None:
        super().__init__(name='DISPATCHER')
        self.middleware = MiddlewareManager()
        self.inner_middleware = MiddlewareManager()
        self.pool: Pool[str, asyncio.Task] = Pool(max_pool_size)
        self.stream_data: dict = {}

    def __setitem__(self, key, value):
        self.stream_data[key] = value

    async def _service_processing(self, metadata: ServiceMessage) -> None:
        """
        This is a standard service handler for working with service messages. Currently, in test mode.

        Command support:

            GET_STATUS - get information about the task

            CLOSING - close a task

        Args:
            metadata (ServiceMessage): The service message to be processed.
        """
        logger.debug(f"Getting service messages: {metadata.command}")
        if metadata.command == Commands.GET_STATUS:
            status: TaskStatus = self.pool.get_status_task(metadata.uuid)
            logger.debug(f"Task-{metadata.uuid} STATUS: {status}")
        elif metadata.command == Commands.CLOSING:
            if metadata.uuid in self.pool:
                self.pool[metadata.uuid].cancel()
                logger.debug(f"The task-{metadata.uuid} was forcibly completed")
            else:
                logger.warning(f"Failed to close the task-{metadata.uuid}, there is no such task in the queue")

    def __cb_close_task(self, future: _asyncio.Task) -> None:
        """
        This is a callback function that is called when a task is completed.
        At the moment, it is created to remove completed tasks from the pool.

        Args:
            future (_asyncio.Task): The future that is completed.
        """
        name = future.get_name()
        self.pool.pop(name)
        logger.debug(f"The task-{name} has been removed from the queue")

    async def listen(self, metadata: Metadata) -> None:
        """
        A function that listens for messages received by the dispatcher that have passed validation

        Args:
            metadata (Message): Data of the message to be processed.
        """
        if isinstance(metadata, ServiceMessage):
            _ = asyncio.create_task(self._service_processing(metadata))
        elif isinstance(metadata, Message):
            task = asyncio.create_task(self._metadata_processing(metadata), name=metadata.uuid)
            task.add_done_callback(self.__cb_close_task)
            self.pool[metadata.uuid] = task

    async def _metadata_processing(self, metadata: Metadata) -> None:
        """
        The first stage of processing is passing through outer middlewares

        Args:
            metadata (Message): Data of the message to be processed.
        """
        data = self.stream_data.copy()

        call_processing: partial = await self.middleware.middleware_processing(handler=self._message_processing, metadata=metadata)
        await call_processing(metadata=metadata, data=data)

    async def _message_processing(self, metadata: Message, data: dict[str, Any]) -> Any:
        """
        The second stage of processing, finding the required processor; Function capture Handling internal middlewares

        Args:
            metadata (Message): Data of the message to be processed.
            data (dict[str, Any]): Message flow data mutated through outer middlewares
        """
        handler: Type[HandlerType] = await find_handler(
            handlers=self.handlers,
            router=self,
            metadata=metadata,
            data=data
        )

        async def _handler_processing(metadata: Message, data: dict[str, Any]) -> Any:
            """
            Running the Handler

            Args:
                metadata (Message): Data of the message to be processed.
                data (dict[str, Any]): Message flow data mutated through outer middlewares
            """
            nonlocal handler
            if isinstance(handler, abc.ABCMeta):
                handler = handler(**get_list_parameters(handler.__init__, metadata=metadata, data=data))

            handler.uuid = metadata.uuid
            fields_cls: dict = get_list_parameters(handler.__call__, metadata=metadata, data=data)
            fields_handle: dict = get_list_parameters(handler.handle, metadata=metadata, data=data, is_handler=True)
            fields_execution_callback: dict = get_list_parameters(handler.on_execution_cb, metadata=metadata, data=data, is_handler=True)
            fields_close_callback: dict = get_list_parameters(handler.on_close_cb, metadata=metadata, data=data, is_handler=True)

            return await handler(**{
                    **fields_cls, **fields_handle,
                    'fields_execution_callback': fields_execution_callback,
                    'fields_close_callback': fields_close_callback
            })

        call_processing: partial | Callable = await self.inner_middleware.middleware_processing(handler=_handler_processing, metadata=metadata)

        return await call_processing(metadata=metadata, data=data)
