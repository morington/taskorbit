import inspect
from dataclasses import asdict
from typing import Callable, Any

from magic_filter import MagicFilter, AttrDict

from taskorbit.filter import FilterType, BaseFilter
from taskorbit.models import Message, TaskMessage


async def evaluate_filters(filters: FilterType, metadata: TaskMessage) -> bool:
    for condition in filters:
        if isinstance(condition, MagicFilter) and not condition.resolve(AttrDict(metadata=metadata)):
            return False
        elif isinstance(condition, bool) and not condition:
            return False
        elif isinstance(condition, BaseFilter) and not await condition(metadata):
            return False
        elif not isinstance(condition, FilterType):  # default
            raise TypeError(
                f"The `filters` must be instances of FilterType, {type(condition).__name__} is not part of this type"
            )

    return True


def validate_filters(filters: FilterType) -> tuple[FilterType]:
    for f in filters:
        if not isinstance(f, FilterType):
            raise TypeError(
                f"The `filters` must be instances of FilterType, {type(f).__name__} is not part of this type"
            )

    if not filters:
        filters = (True, )

    return filters


def get_list_parameters(func: Callable, metadata: TaskMessage) -> dict[str, Any]:
    _metadata = asdict(metadata)
    data = _metadata.pop('context_data')
    data['message'] = Message(**_metadata)

    _sig = inspect.signature(func)
    return {param: value for param, value in data.items() if param in _sig.parameters}




