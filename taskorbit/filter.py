from abc import ABC, abstractmethod
from typing import Union

from magic_filter import MagicFilter

from taskorbit.models import Message


#  Under development!!!
class BaseFilter(ABC):
    @abstractmethod
    async def __call__(self, metadata: Message) -> bool: ...


FilterType = Union[MagicFilter, BaseFilter, bool, tuple]
