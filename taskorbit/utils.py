import inspect
import logging
from types import NoneType
from typing import Callable, Any

from magic_filter import MagicFilter, AttrDict

from taskorbit.filter import FilterType, BaseFilter
from taskorbit.models import Message


logger = logging.getLogger(__name__)


async def evaluate_filters(filters: FilterType, *args, **kwargs) -> bool:
    """
    Filters need to be improved!!!!!!!!
    """
    for condition in filters:
        if isinstance(condition, MagicFilter) and not condition.resolve(AttrDict(*args, **kwargs)):
            return False
        elif isinstance(condition, bool) and not condition:
            return False
        # elif isinstance(condition, BaseFilter) and not await condition(metadata):
        #     return False
        elif not isinstance(condition, FilterType):  # default
            raise TypeError(f"The `filters` must be instances of FilterType, {type(condition).__name__} is not part of this type")

    return True


def validate_filters(filters: FilterType) -> tuple[FilterType]:
    for f in filters:
        if not isinstance(f, FilterType):
            raise TypeError(f"The `filters` must be instances of FilterType, {type(f).__name__} is not part of this type")

    if not filters:
        filters = (True,)

    return filters


def get_list_parameters(func: Callable, metadata: Message, data: dict[str, Any], is_handler: bool = False) -> dict[str, Any]:
    if isinstance(func, NoneType):
        return {}
    else:
        _sig = inspect.signature(func)
        _data = {**data} if is_handler else {"data": data}
        return {param: value for param, value in {"metadata": metadata, **_data}.items() if param in _sig.parameters}
