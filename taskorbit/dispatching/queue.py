import asyncio
from typing import Optional

from taskorbit.types import TaskStatus


class Queue(dict):
    def __init__(self, max_size: Optional[int] = None) -> None:
        super().__init__()
        if max_size is None:
            raise ValueError("Queue cannot be NoneType. For an unlimited queue, use 0.")

        self.max_size = max_size

    def __setitem__(self, key: str, value: asyncio.Task):
        value.set_name(key)
        super().__setitem__(key, value)

    def pop(self, key, default=None):
        print(f"Это функция очереди {self}")
        s = super().pop(key, default)
        print(f"Это функция очереди {self}")
        return s

    @property
    def full(self) -> bool:
        return len(self) >= self.max_size

    def close_task(self, uuid: str) -> None:
        if uuid in self:
            task = self.pop(uuid)
            task.cancel()

    def get_status_task(self, uuid: str) -> TaskStatus:
        if uuid in self:
            return TaskStatus.RUNNING
        else:
            return TaskStatus.UNKNOWN
