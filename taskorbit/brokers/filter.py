from abc import ABC, abstractmethod

from taskorbit.models import TaskMessage


class BaseFilter(ABC):
    @abstractmethod
    async def __call__(self, metadata: TaskMessage) -> bool: ...
