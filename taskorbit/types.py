from typing import Union, Callable, Awaitable

from magic_filter import MagicFilter

from taskorbit.brokers.filter import BaseFilter
from taskorbit.dispatching.basehandler import BaseHandler
from taskorbit.models import TaskMessage, ServiceMessage


FilterType = Union[MagicFilter, BaseFilter, bool, tuple]
Metadata = Union[TaskMessage | ServiceMessage]
HandlerType = Union[BaseHandler, Callable[[TaskMessage], Awaitable[None]]]
