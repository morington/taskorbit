import logging
from abc import ABC, abstractmethod
from typing import Callable, Any

from taskorbit.models import Message


logger = logging.getLogger(__name__)


class Middleware(ABC):
    @abstractmethod
    async def __call__(self, handler: Callable, metadata: Message, data: dict[str, Any]) -> Any: ...
