import logging
from typing import Optional

from taskorbit.enums import TaskStatus


logger = logging.getLogger(__name__)


class Queue(dict):
    def __init__(self, max_size: Optional[int] = None) -> None:
        super().__init__()
        if max_size is None:
            raise ValueError("Queue cannot be NoneType. For an unlimited queue, use 0.")

        self.max_size = max_size

    @property
    def full(self) -> bool:
        return len(self) >= self.max_size

    def close_task(self, name: str) -> None:
        if name in self:
            task = self.pop(name)
            task.cancel(self)

    def get_status_task(self, uuid: str) -> TaskStatus:
        if uuid in self:
            return TaskStatus.RUNNING
        else:
            return TaskStatus.UNKNOWN
