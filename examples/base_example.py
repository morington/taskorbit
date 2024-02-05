import asyncio
import uuid
from typing import Callable, Any

import structlog
from magic_filter import F

import setup_logger
from taskorbit import Dispatcher, Router, Middleware, Message, BaseHandler, Metadata
from taskorbit.brokers.nats.client import nats_broker
from taskorbit.enums import Commands

logger = structlog.getLogger(__name__)

# Please create a dispatcher with 3 maximum tasks at the same time
dp = Dispatcher(max_queue_size=3)
# Use routers to expand your service more flexibly
router = Router()


class DatabasePoolSimulation:
    def __enter__(self):
        logger.debug("Connecting to the database--->")

    def __exit__(self, exc_type, exc_value, traceback):
        logger.debug("<----Returning the session to the pool")


class MyMiddleware(Middleware):
    """
    An example of a simple middleware is shown.
    It allows processing incoming data before handler detection (middleware) and after detection (outer_middleware).
    You can pass data to both init and call.
    """

    def __init__(self, my_age: int):
        self.my_age = my_age

    async def __call__(self, handler: Callable, metadata: Message, data: dict[str, Any]) -> Any:
        """
        Implementation of a database connection simulation so that you can ensure that the context manager does not interrupt in middlewares.
        """
        with DatabasePoolSimulation():
            logger.debug("Starting my middleware")
            name = data.get("name", None)
            if name:
                data["name"] = f"{name} [{self.my_age} yo]"

            return await handler(metadata, data)


async def main():
    """
    We can either explicitly go through the broker configuration steps,
    or we can use lazy fetching via the `nats_broker` function
    """
    # broker = NatsBroker({
    #         "url": "nats://localhost:4222",
    #         "stream": "test_nats",
    #         "subject": "test_nats.test",
    #         "durable": "test_nats_durable",
    # })
    #
    # await broker.startup()

    broker = await nats_broker(
        {
            "url": "nats://localhost:4222",
            "stream": "test_nats",
            "subject": "test_nats.test",
            "durable": "test_nats_durable",
        }
    )

    """
    To give you an example, I'll send some data to the broker so my handlers can process it
    """
    # Using service messages to work with tasks. In this example we will close our first task
    _uuid = uuid.uuid4().hex
    await broker.pub({"uuid": _uuid, "type_event": "TEST_CLASS", "data": {"some_data": 123}})
    await broker.pub({"uuid": _uuid, "command": Commands.GET_STATUS})
    await broker.pub({"uuid": _uuid, "command": Commands.CLOSING})
    await broker.pub({"uuid": _uuid, "command": Commands.GET_STATUS})

    # These tasks will execute, but the 4th task will wait for the others to execute, because we have specified in
    # the dispatcher no more than 3 processes at the same time.
    # The task is sent back to the broker and will return soon.
    # --> UPD: Service messages no longer load the queue. All service messages are executed out of queue.
    await broker.pub({"uuid": uuid.uuid4().hex, "type_event": "TEST_CLASS", "data": {"some_data": 123}})
    await broker.pub({"uuid": uuid.uuid4().hex, "type_event": "TEST_FUNCTION", "data": {"some_data": 123}})
    await broker.pub({"uuid": uuid.uuid4().hex, "type_event": "TEST_CLASS", "data": {"some_data": 123}})

    """
    I can send some data directly to the dispatcher.
    I can use middleware to mutate the data.
    Here I use an internal middleware that will only execute if it finds a handler to process it.
    Maybe the filters are currently not conveniently done, I will think about it in the future.

    I'll also initialize our router.
    """
    dp["name"] = "Adam"
    dp.inner_middleware.include(MyMiddleware(25), F.metadata.type_event == "TEST_CLASS")
    dp.include_router(router)

    """
    Let's start our broker polling, enter our dispatcher into it
    """
    logger.debug("Start...")
    await broker.include_dispatcher(dp)


@dp.include_class_handler(F.metadata.type_event == "TEST_CLASS")
class MyHandler(BaseHandler):
    """
    This is the first option for creating a handler through a class.
    It may be more convenient for someone to use classes to group stages of processing their business logic.
    """

    def __init__(self, metadata: Metadata) -> None:
        super().__init__()
        """
        :param uuid: str - Unique task id
        :param execution_timeout: Optional[int] = None - Timeout for waiting.
            After which the `on_execution_timeout` callback is executed. By default, just the log is output.
        :param on_execution_timeout: Optional[Callable[[], Awaitable[None]]] = None - Callback triggered after timeout
            time expires
        :param close_timeout: Optional[int] = None - Timeout for closure.
            After this time expires, the `on_close` callback is executed. By default, only the log is output.
        :param on_close: Optional[Callable[[], Awaitable[None]]] = None - The callback triggered when the task
            timeout has expired closes the current task. By default it outputs a log.
        """
        self.uuid = metadata.uuid

        # After 2 seconds, please display the log that you need to wait more
        self.execution_timeout = 2
        # Please close the task if it runs for more than 7 seconds
        self.close_timeout = 7

    async def handle(self, name: str) -> None:
        """
        Simulation of business logic operation
        """
        logger.info(f"{name}, Run....")
        await asyncio.sleep(4)
        logger.info(f"{name}, Done!")


@router.include_handler(F.metadata.type_event == "TEST_FUNCTION")
async def handle_function(metadata: Message, name: str) -> None:
    """
    Easy function, we can still set timeouts and callbacks for them. This is done in the decorator.
    This is a simple variant of the handler.

    Simulation of business logic operation
    """
    logger.info(f"{name}, function-handler is complete!")


if __name__ == "__main__":
    asyncio.run(main())
