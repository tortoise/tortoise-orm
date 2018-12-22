from enum import Enum
from typing import TypeVar, Type

from tortoise import ConfigurationError
from tortoise.fields import CharField

T = TypeVar("T")


class EnumField(CharField):
    """
    An example extension to CharField that serializes Enums
    to and from a Text representation in the DB.
    """

    def __init__(self, enum_type: Type[T], *args, **kwargs):
        super().__init__(128, *args, **kwargs)
        if not issubclass(enum_type, Enum):
            raise ConfigurationError("{} is not a subclass of Enum!".format(enum_type))
        self._enum_type = enum_type

    def to_db_value(self, value: T, instance) -> str:
        return value.value

    def to_python_value(self, value: str) -> T:
        try:
            return self._enum_type(value)
        except Exception:
            raise ValueError(
                "Database value {} does not exist on Enum {}.".format(value, self._enum_type)
            )
