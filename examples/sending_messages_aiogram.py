import asyncio
import uuid

import structlog
from magic_filter import F
from aiogram import Bot
from aiogram.enums import ParseMode
from taskorbit import Router, Dispatcher, Metadata
from taskorbit.brokers.nats.client import nats_broker


# I use my own template to handle the logs.
# I always use the Structlog library. In my opinion it is one of the best in its field.
import setup_logger
logger = structlog.getLogger(__name__)
# Let's remember to use our routers! Thanks to them, we will be able to work more flexibly with our project.
# It is not necessary to write everything in one file, split them into several files by topics.
router = Router()


@router.include_handler(F.metadata.type_event == "SENDING")
async def handler_sending(metadata: Metadata, bot: Bot):
    """
    Our newsletter isn't going to be some super serious newsletter. I'm here to show you how to do it, and the rest is in your hands.
    We're just sending what we got. Specifically kwargs: chat_id and text
    """
    await bot.send_message(**metadata.data)


async def main():
    broker = await nats_broker(
        {
            "url": "nats://localhost:4222",
            "stream": "test_nats",
            "subject": "test_nats.test",
            "durable": "test_nats_durable",
        }
    )

    """
    To avoid creating a separate bot in this scenario, we implement a simulation scheme.
    Of course, in a natural environment IDs are taken from the database and also sent to NATS JetStream.
    """
    text = "Hey, buddy! This is a newsletter on taskorbit!"
    for user_id in [589294145, 655021211, 651998237]:
        await broker.pub({"uuid": uuid.uuid4().hex, "type_event": "SENDING", "data": {"chat_id": user_id, "text": text}})

    """
    Again, I don't want to complicate the example, I added my token to the environment variables, I won't register the configs.
    """
    import dotenv, os
    dotenv.load_dotenv()

    bot_settings = {
        "parse_mode": ParseMode.HTML,
        "disable_web_page_preview": True,
        "token": os.environ.get("TOKEN")
    }
    bot = Bot(**bot_settings)

    """
    Let's create our dispatcher for example for 5 parallel tasks. And also added to the context data of our bot.
    """
    dp = Dispatcher(max_queue_size=5)
    dp['bot']: Bot = bot
    dp.include_router(router)

    await broker.include_dispatcher(dp)


if __name__ == "__main__":
    asyncio.run(main())
