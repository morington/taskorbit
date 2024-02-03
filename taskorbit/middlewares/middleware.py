from taskorbit.models import TaskMessage


class Middleware:
    async def __call__(self, metadata: TaskMessage) -> TaskMessage:
        ...
