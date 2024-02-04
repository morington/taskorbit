import logging
import asyncio
from typing import Optional

from taskorbit.enums import TaskStatus
from taskorbit.utils import get_list_parameters


logger = logging.getLogger(__name__)


class Queue(dict):
    def __init__(self, max_size: Optional[int] = None) -> None:
        super().__init__()
        if max_size is None:
            raise ValueError("Queue cannot be NoneType. For an unlimited queue, use 0.")

        self.max_size = max_size

    def __setitem__(self, key: str, value: tuple):
        if not isinstance(value, tuple):
            raise ValueError("Queue `value` must be `tuple`")

        handler, type_handler, metadata = value
        fields_cls: dict = get_list_parameters(handler.__call__, metadata)
        fields_handle: dict = get_list_parameters(handler.handle, metadata)
        asyncio.create_task(handler.__call__(queue=self, **{**fields_cls, **fields_handle}))
        super().__setitem__(key, handler)

    @property
    def full(self) -> bool:
        return len(self) >= self.max_size

    def close_task(self, uuid: str) -> None:
        if uuid in self:
            handler = self.pop(uuid)
            handler.cancel(self)

    def get_status_task(self, uuid: str) -> TaskStatus:
        if uuid in self:
            return TaskStatus.RUNNING
        else:
            return TaskStatus.UNKNOWN
