from typing import Optional, Any

import nats
import logging
from nats.aio.client import Client
from nats.js import JetStreamContext
from nats.js.errors import NotFoundError
from ormsgpack import ormsgpack

from taskorbit.brokers.nats.configuration import NatsConfiguration
from taskorbit.dispatching.dispatcher import Dispatcher
from taskorbit.models import TaskMessage, ServiceMessage

logger = logging.getLogger(__name__)


class NatsBroker:
    jetstream: Optional[JetStreamContext]

    def __init__(self, config: dict[str, str] | NatsConfiguration) -> None:
        if isinstance(config, dict):
            config = NatsConfiguration(**config)

        self.config = config

    async def startup(self):
        nats_connect: Client = await nats.connect(self.config.url)
        self.jetstream: JetStreamContext = nats_connect.jetstream()

    async def _get_subscriber(self) -> JetStreamContext.PushSubscription:
        return await self.jetstream.subscribe(
            stream=self.config.stream,
            subject=self.config.subject,
            durable=self.config.durable
        )

    async def _creating_stream(self) -> None:
        await self.jetstream.add_stream(
            name=self.config.stream,
            subjects=[self.config.subject]
        )

    async def _builder_subscriber(self) -> JetStreamContext.PushSubscription:
        if self.jetstream is None:
            raise RuntimeError("JetStream is not initialized")

        try:
            return await self._get_subscriber()
        except NotFoundError:
            await self._creating_stream()
            return await self._get_subscriber()

    async def include_dispatcher(self, dp: Dispatcher) -> None:
        if not isinstance(dp, Dispatcher):
            raise TypeError(f"The `middleware` must be an instance of Middleware, but received {type(dp).__name__}")

        if self.jetstream is None:
            await self.startup()

        subscriber: JetStreamContext.PushSubscription = await self._builder_subscriber()
        async for msg in subscriber.messages:
            print("New msg", not dp.queue.full, [task for task in dp.queue.keys()])
            if not dp.queue.full:
                data: dict[str, Any] | int = ormsgpack.unpackb(msg.data)

                if isinstance(data, int):
                    logger.warning(f"The message has an unknown format: {data}")
                else:
                    fields_data = set(data.keys())
                    # try:
                    if TaskMessage.validate_fields(fields_data):
                        metadata: TaskMessage = TaskMessage(**data)
                    elif ServiceMessage.validate_fields(fields_data):
                        metadata: ServiceMessage = ServiceMessage(**data)
                    else:
                        raise TypeError(f"The message has an unknown format: {fields_data}")

                    await dp.listen(metadata=metadata)
                    # except TypeError as exc:
                    #     logger.error(f"TypeError: {exc.args[0]}")
                    # except Exception as exc:
                    #     logger.error(f"Exception: {exc}")

                await msg.ack()
