import abc
import asyncio
import logging
from typing import Optional, Type

from taskorbit.dispatching.queue import Queue
from taskorbit.dispatching.router import Router
from taskorbit.middlewares.manager import MiddlewareManager
from taskorbit.types import TaskMessage, HandlerType, Metadata, ServiceMessage, Commands, TaskStatus
from taskorbit.utils import get_list_parameters


logger = logging.getLogger(__name__)


class Dispatcher(Router):
    def __init__(self, max_queue_size: int) -> None:
        super().__init__()
        self.middleware = MiddlewareManager()
        self.outer_middleware = MiddlewareManager()
        self.queue: Queue[str, asyncio.Task] = Queue(max_queue_size)
        self.context_data: dict = {}

    def __setitem__(self, key, value):
        self.context_data[key] = value

    async def __processing_service_messages(self, metadata: ServiceMessage) -> None:
        if metadata.command == Commands.GET_STATUS:
            result: TaskStatus = self.queue[metadata.uuid]
            logger.debug(f"Task {metadata.uuid} is {result}")
        elif metadata.command == Commands.CLOSING:
            self.queue.close_task(metadata.uuid)
            logger.debug(f"Task {metadata.uuid} is closing")

    async def __processing_task_messages(self, metadata: TaskMessage) -> None:
        handler: Optional[Type[HandlerType]] = await self.find_handler(metadata=metadata)
        if handler is None:
            raise RuntimeError("Handler not found")

        metadata: Metadata = await self.outer_middleware(metadata=metadata)

        if isinstance(handler, abc.ABCMeta):
            class_instance = handler(**get_list_parameters(handler.__init__, metadata))
            self.queue[metadata.uuid] = asyncio.create_task(
                class_instance.__call__(queue=self.queue, **get_list_parameters(class_instance.__call__, metadata))
            )
            print(self.queue)
        else:
            self.queue[metadata.uuid] = asyncio.create_task(handler(**get_list_parameters(handler, metadata)))

    async def listen(self, metadata: Metadata) -> None:
        metadata.context_data = self.context_data

        metadata: Metadata = await self.middleware(metadata=metadata)

        if isinstance(metadata, ServiceMessage):
            await self.__processing_service_messages(metadata)
        elif isinstance(metadata, TaskMessage):
            await self.__processing_task_messages(metadata)

