<p align="center">
    <img src="https://raw.githubusercontent.com/morington/taskorbit/main/docs/assets/images/taskorbit.png" alt="taskorbit-logo" height="200" />
</p>

<h1 align="center">TaskOrbit: Effortless Tasking</h1>
<h3 align="center">An asynchronous framework for Python with efficient task pooling that provides simple and flexible management of asynchronous execution of independent tasks.</h3>

<p align="center">
    <a href="#" target="_blank">
        <img alt="Status" src="https://img.shields.io/pypi/status/taskorbit.svg?style=flat-square">
    </a>
    <a href="#" target="_blank">
        <img alt="PyPI" src="https://img.shields.io/pypi/v/taskorbit.svg?style=flat-square">
    </a>
    <a href="#" target="_blank">
        <img alt="Python" src="https://img.shields.io/pypi/pyversions/taskorbit.svg">
    </a>
    <a href="#" target="_blank">
        <img alt="Python" src="https://img.shields.io/github/license/morington/taskorbit">
    </a>
    <a href="https://t.me/+0ih_O4_AkhlkMThi" target="_blank">
        <img alt="Python" src="https://img.shields.io/endpoint?url=https%3A%2F%2Ftelegram-badge-4mbpu8e0fit4.runkit.sh%2F%3Furl%3Dhttps%3A%2F%2Ft.me%2F%2B0ih_O4_AkhlkMThi&label=Community">
    </a>
</p>

# Taskorbit

<b>Taskorbit</b> is an asynchronous framework for managing a queue of asynchronous tasks. Inspired by ideas from [Celery](https://github.com/celery/celery), [Taskiq](https://github.com/taskiq-python/taskiq), [Propan](https://github.com/Lancetnik/Propan) and [Aiogram](https://github.com/aiogram/aiogram). This framework is based on message brokers. Currently, there is only support for [NATS JetStream](https://github.com/nats-io/nats.py). An expansion is planned for the future.

The framework allows you to create a powerful service for processing any tasks of any complexity in a short time. Entry is minimal, the development was oriented on beginners in the world of bot building and microservices development.

We can say simply - it is an improved version of Celery, Taskiq, Propan in the style of Aiogram. The differences are in specific requirements. It is important to choose technologies carefully to achieve optimal results.

<b>Documentation is currently being developed and will be available at: https://morington.github.io/taskorbit/</b>

# Install

Use the pip tool to install the framework:

```commandline
pip install taskorbit
```

Currently, with support for the NATS message broker only, variable installation with the broker is not supported. The library will install the necessary dependencies if required.

Taskorbit currently includes:
- <b>[magic_filter](https://github.com/aiogram/magic-filter)</b> - a handy way to enable dynamic signatures, created by the Aiogram developers.
- <b>[ormsgpack](https://github.com/aviramha/ormsgpack)</b> - a quick way to serialize data.
- <b>[nats-py](https://github.com/nats-io/nats.py)</b> - a standard message broker.

# Quick start

<i>You can read the full example on the repository page: https://github.com/morington/taskorbit/blob/main/examples/base_example.py.</i>

Create a broker object, distpecker object in your asynchronous function, load the configuration and start receiving messages!

```python
# For the example I will not use routers, the dispatcher inherits from routers so can also integrate handlers.
# DON'T DO THIS! USE taskorbit.dispatching.Router !
dp = Dispatcher(max_queue_size=5)


@dp.include_handler(F.metadata.type_event == "Test")
async def handler_test(metadata: Metadata) -> None:
    logger.info(f"Handler got the message! Task-{metadata.uuid}")


async def main():
    broker = await nats_broker(
        {
            "url": "nats://localhost:4222",
            "stream": "STREAM_NAME",
            "subject": "STREAM_NAME.SUBJECT",
            "durable": "DURABLE",
        }
    )
	
    await broker.include_dispatcher(dp)


if __name__ == "__main__":
    asyncio.run(main())
```

# Models metadata

<b>At the moment, development is underway on out-of-the-box custom message models. Please wait, the standard Metadata model is currently available for both service messages and task data messages:</b>

```python
class Message(BaseType):
    uuid: str
    type_event: str
    data: Optional[dict] = None


@dataclass
class ServiceMessage(BaseType):
    uuid: str
    command: Commands
```

# Sending messages

You can send messages to a thread using the pub method. Generate a unique UUID for each message to handle each shuffle:

```python
# Data messages for tasks:
uuid = uuid.uuid4().hex
await broker.pub({"uuid": uuid, "type_event": "TEST_CLASS", "data": {"some_data": 123}}))

# Service messages to work with tasks
# Service messages are not stored in the task pool. It needs to send the UUID it will work with
await broker.pub({"uuid": uuid, "command": Commands.GET_STATUS})
```

The framework also supports outer-middlewares and inner-middlewares. Middlewares fully support context managers throughout task processing.

<b>Currently, the Filters classes are disabled. Under testing.</b>

Please don't forget to refer to [EXAMPLES](https://github.com/morington/taskorbit/tree/main/examples) in the repository structure for help with the framework. Stable examples that have been tested are posted there.

# License:

Taskorbit is distributed under the MIT license. Details can be found in the [LICENSE](https://raw.githubusercontent.com/morington/taskorbit/main/LICENSE) file.


