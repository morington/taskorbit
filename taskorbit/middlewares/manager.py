import logging
from functools import partial
from typing import Callable

from taskorbit.filter import FilterType
from taskorbit.middlewares.middleware import Middleware
from taskorbit.models import Metadata
from taskorbit.utils import evaluate_filters, validate_filters


logger = logging.getLogger(__name__)


class MiddlewareManager:
    def __init__(self) -> None:
        self.middlewares: dict[Middleware, tuple[FilterType, ...]] = {}

    async def middleware_processing(self, handler: Callable, metadata: Metadata) -> partial | Callable:
        for middleware, filters in self.middlewares.items():
            if await evaluate_filters(filters, metadata=metadata):
                handler: partial = partial(middleware, handler=handler)

        return handler

    def include(self, middleware: Middleware, *filters: FilterType) -> None:
        if not isinstance(middleware, Middleware):
            raise TypeError(f"The `middleware` must be an instance of Middleware, but received {type(middleware).__name__}")

        self.middlewares[middleware] = validate_filters(filters)
