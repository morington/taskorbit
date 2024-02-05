import logging
import uuid
from typing import Optional, Type, Callable, Any

from taskorbit.dispatching.handler import HandlerType, Handler
from taskorbit.filter import FilterType
from taskorbit.models import Message
from taskorbit.utils import validate_filters, evaluate_filters


logger = logging.getLogger(__name__)


class Router:
    def __init__(self, name: str = uuid.uuid4().hex) -> None:
        self.name = name
        self.child_routers: dict["Router", tuple[FilterType, ...]] = {}
        self.handlers: dict[Type[HandlerType], tuple[FilterType, ...]] = {}

    def __str__(self) -> str:
        return f"<Router:{self.name}>"

    def __repr__(self) -> str:
        return self.__str__()

    def include_router(self, router: "Router", *filters: FilterType) -> None:
        if not isinstance(router, Router):
            raise TypeError(f"The router must be an instance of Router, but received {type(router).__name__}")

        self.child_routers[router] = validate_filters(filters)

    def include_class_handler(self, *filters: FilterType) -> Type[HandlerType]:
        def wrapper(cls: HandlerType):
            self.handlers[cls] = validate_filters(filters)
            return cls

        return wrapper

    def include_handler(
        self,
        *filters: FilterType,
        execution_timeout: Optional[int] = None,
        on_execution_timeout: Optional[Callable] = None,
        close_timeout: Optional[int] = None,
        on_close: Optional[Callable] = None,
    ) -> Callable:
        def wrapper(handler: Callable):
            cls = Handler()
            cls.name = handler.__name__
            cls.execution_timeout = execution_timeout
            cls.on_execution_timeout = on_execution_timeout
            cls.close_timeout = close_timeout
            cls.on_close = on_close
            cls.handle = handler
            self.handlers[cls] = validate_filters(filters)
            return handler

        return wrapper


async def find_handler(
        handlers: dict[Type[HandlerType], tuple[FilterType, ...]],
        router: Router,
        metadata: Message,
        data: dict[str, Any],
        _child: bool = False
) -> Optional[Type[HandlerType]]:
    for handler, handler_filters in handlers.items():
        if await evaluate_filters(filters=handler_filters, metadata=metadata, data=data):
            return handler

    for child_router, router_filters in router.child_routers.items():
        if await evaluate_filters(filters=router_filters, metadata=metadata, data=data):
            child_handler = await find_handler(handlers=child_router.handlers, router=child_router, metadata=metadata, data=data, _child=True)
            if child_handler:
                return child_handler

    if not _child:
        raise RuntimeError("Handler not found")
