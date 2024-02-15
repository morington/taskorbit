from typing import Optional, Any

import nats
import logging
from nats.aio.client import Client
from nats.js import JetStreamContext
from nats.js.errors import NotFoundError, NoStreamResponseError
from ormsgpack import ormsgpack

from taskorbit.brokers.nats.configuration import NatsConfiguration
from taskorbit.dispatching.dispatcher import Dispatcher
from taskorbit.models import Message, ServiceMessage

logger = logging.getLogger(__name__)


class NatsBroker:
    """
    NatsBroker is an implementation of a client broker that uses NATS.

    Args:
        config (dict[str, str] | NatsConfiguration): The configuration of the broker. You can either pass a dictionary with the configuration parameters
        or an instance of the NatsConfiguration class.

    Attributes:
        jetstream (Optional[JetStreamContext]): You will need the JetStream context to make any JetStream enabled
        operation.
    """
    jetstream: Optional[JetStreamContext]

    def __init__(self, config: dict[str, str] | NatsConfiguration) -> None:
        if isinstance(config, dict):
            config = NatsConfiguration(**config)

        self.config = config

    async def startup(self) -> None:
        """
        Connects to NATS and creates a JetStream context.
        """
        nats_connect: Client = await nats.connect(self.config.url)
        self.jetstream: JetStreamContext = nats_connect.jetstream()

    async def pub(self, data: dict[str, Any]) -> None:
        """
        Publishes a message to NATS.

        Args:
            data (dict[str, Any]): The data to be published. The data will be serialized using ormsgpack.

        :return: None
        """
        async def _publish():
            await self.jetstream.publish(
                stream=self.config.stream,
                subject=self.config.subject,
                payload=ormsgpack.packb(data),
            )

        try:
            await _publish()
        except NoStreamResponseError:
            await self._creating_stream()
            await _publish()

    async def _get_subscriber(self) -> JetStreamContext.PushSubscription:
        """
        Returns a JetStream push subscription.

        :return: JetStreamContext.PushSubscription
        """
        return await self.jetstream.subscribe(
            stream=self.config.stream,
            subject=self.config.subject,
            durable=self.config.durable,
        )

    async def _creating_stream(self) -> None:
        """
        Creates a JetStream push subscription.

        :return: None
        """
        await self.jetstream.add_stream(name=self.config.stream, subjects=[self.config.subject])

    async def _builder_subscriber(self) -> JetStreamContext.PushSubscription:
        """
        Returns a JetStream push subscription. If the stream does not exist, it will be created. If JetStream is not initialized, raises an error.

        :return: JetStreamContext.PushSubscription
        """
        if self.jetstream is None:
            raise RuntimeError("JetStream is not initialized")

        try:
            return await self._get_subscriber()
        except NotFoundError:
            await self._creating_stream()
            return await self._get_subscriber()

    async def include_dispatcher(self, dp: Dispatcher) -> None:
        """
        Adds a dispatcher to the broker's client for wiretapping. Messages that fit the data model will be given to it for subsequent detection of the handler.

        Args:
            dp (Dispatcher): The dispatcher to be added.

        :return: None
        """
        if not isinstance(dp, Dispatcher):
            raise TypeError(f"The `middleware` must be an instance of Middleware, but received {type(dp).__name__}")

        if self.jetstream is None:
            await self.startup()

        subscriber: JetStreamContext.PushSubscription = await self._builder_subscriber()

        async for msg in subscriber.messages:
            logger.debug(f"New msg! Is the queue full? - {dp.pool.full}; {len(dp.pool)}")
            data: dict[str, Any] | int = ormsgpack.unpackb(msg.data)

            if isinstance(data, int):
                logger.warning(f"The message has an unknown format: {data}")
            else:
                fields_data = set(data.keys())
                is_service_message = ServiceMessage.validate_fields(fields_data)

                # SERVICE_MESSAGE
                if is_service_message:
                    try:
                        metadata: ServiceMessage = ServiceMessage(**data)
                        await dp.listen(metadata=metadata)
                    except TypeError as exc:
                        logger.error(f"TypeError: {exc}")
                    await msg.ack()
                    continue

                # MESSAGE
                if not dp.pool.full:
                    try:
                        if Message.validate_fields(fields_data):
                            metadata: Message = Message(**data)
                        else:
                            raise TypeError(f"The message has an unknown format: {fields_data}")

                        await dp.listen(metadata=metadata)
                    except TypeError as exc:
                        logger.error(f"TypeError: {exc}")

                    await msg.ack()
                else:
                    logger.debug("Queue is full, skipping message acknowledgment.")


async def nats_broker(config: dict[str, str] | NatsConfiguration) -> NatsBroker:
    """
    Lazily creates an instance of the NatsBroker class.

    Args:
        config (dict[str, str] | NatsConfiguration): The configuration of the broker. You can either pass a dictionary with the configuration parameters
        or an instance of the NatsConfiguration class.

    :return: NatsBroker
    """
    broker = NatsBroker(config)
    await broker.startup()
    return broker
