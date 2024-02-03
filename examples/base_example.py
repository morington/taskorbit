import asyncio
import uuid

import ormsgpack

import setup_logger
from taskorbit.dispatching.basehandler import BaseHandler
from taskorbit.brokers.nats.client import NatsBroker
from taskorbit.dispatching.dispatcher import Dispatcher
from taskorbit.enums import Commands
from taskorbit.models import Metadata

dp = Dispatcher(3)


async def main():
    # Загружаем конфигурацию.
    broker = NatsBroker(
        {
            "url": "nats://localhost:4222",
            "stream": "test_nats",
            "subject": "test_nats.test",
            "durable": "test_nats_durable",
        }
    )

    # Для публикации сообщений реализуем подключение.
    await broker.startup()

    # Тестовые сообщения в стрим NATS
    async def pub(data):
        await broker.jetstream.publish(
            stream="test_nats", subject="test_nats.test", payload=ormsgpack.packb(data)
        )

    _uuid = uuid.uuid4().hex
    await pub({"uuid": _uuid, "data": {"chat_id": 123}})

    await pub({"uuid": uuid.uuid4().hex, "data": {"chat_id": 123}})

    await pub({"uuid": _uuid, "command": Commands.CLOSING})

    # Эта задача не отправится сразу в обработку, так как мы выставили 3 максимальных процесса в диспетчере.
    # На текущий момент сервисные сообщения входят в размер очереди.
    await pub({"uuid": uuid.uuid4().hex, "data": {"chat_id": 123}})

    # Подключаем поллинг на наш диспетчер
    await broker.include_dispatcher(dp)


# Наш простой воркер в виде класса.
@dp.include_class(True)
class MyHandler(BaseHandler):
    def __init__(self, message: Metadata) -> None:
        super().__init__()
        self.uuid = message.uuid
        self.execution_timeout = 2
        self.close_timeout = 7

    # Реализация симуляции ожидания. Здесь наша бизнес-логика.
    async def handle(self) -> None:
        print("Run....")
        await asyncio.sleep(4)
        print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
