from typing import Optional, Type, Callable

from taskorbit.dispatching.handler import HandlerType, Handler
from taskorbit.filter import FilterType
from taskorbit.models import TaskMessage
from taskorbit.utils import validate_filters, evaluate_filters


class Router:
    def __init__(self) -> None:
        self.child_routers: dict["Router", tuple[FilterType, ...]] = {}
        self.handlers: dict[Type[HandlerType], tuple[FilterType, ...]] = {}

    def include_router(self, router: "Router", *filters: FilterType) -> None:
        if not isinstance(router, Router):
            raise TypeError(
                f"The router must be an instance of Router, but received {type(router).__name__}"
            )

        self.child_routers[router] = validate_filters(filters)

    async def find_handler(self, metadata: TaskMessage) -> Optional[Type[HandlerType]]:
        return await self.recursive_router_search(metadata)

    async def recursive_router_search(
        self, metadata: TaskMessage
    ) -> Optional[Type[HandlerType]]:
        for handler, handler_filters in self.handlers.items():
            if await evaluate_filters(handler_filters, metadata):
                return handler

        for child_router, router_filters in self.child_routers.items():
            if await evaluate_filters(router_filters, metadata):
                child_handler = await child_router.recursive_router_search(metadata)
                if child_handler:
                    return child_handler

        return None

    def include_class_handler(self, *filters: FilterType) -> Type[HandlerType]:
        def wrapper(cls: HandlerType):
            self.handlers[cls] = validate_filters(filters)
            return cls

        return wrapper

    def include_handler(
            self, *filters: FilterType,
            execution_timeout: Optional[int] = None, on_execution_timeout: Optional[Callable] = None,
            close_timeout: Optional[int] = None, on_close: Optional[Callable] = None
    ) -> Callable:
        def wrapper(handler: Callable):
            cls = Handler()
            cls.execution_timeout = execution_timeout
            cls.on_execution_timeout = on_execution_timeout
            cls.close_timeout = close_timeout
            cls.on_close = on_close
            cls.handle = handler
            self.handlers[cls] = validate_filters(filters)
            return handler

        return wrapper
