from dataclasses import dataclass, fields
from enum import EnumMeta
from typing import Optional, Union

from taskorbit.enums import Commands


@dataclass
class BaseType:
    def __post_init__(self):
        for field in fields(self):
            attr_sel = getattr(self, field.name)
            if isinstance(field.type, EnumMeta):
                if field.type.validate_key(attr_sel):
                    setattr(self, field.name, field.type[attr_sel])
            elif not isinstance(attr_sel, field.type):
                raise TypeError(f"Invalid nested type: {field.name}: {type(attr_sel).__name__} != {field.type.__name__}")

    @classmethod
    def validate_fields(cls, data: set[str]) -> bool:
        if not isinstance(data, set):
            raise TypeError(f"The `data` must be a set, but received {type(data).__name__}")

        return data == {field.name for field in fields(cls) if field.default is not None or field.name in data}


@dataclass
class Message(BaseType):
    uuid: str
    type_event: str
    data: Optional[dict] = None


@dataclass
class ServiceMessage(BaseType):
    uuid: str
    command: Commands


Metadata = Union[Message, ServiceMessage]
