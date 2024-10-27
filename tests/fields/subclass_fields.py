from enum import Enum, IntEnum
from typing import Any, Type

from tortoise import ConfigurationError
from tortoise.fields import CharField, IntField


class EnumField(CharField):
    """
    An example extension to CharField that serializes Enums
    to and from a Text representation in the DB.
    """

    __slots__ = ("enum_type",)

    def __init__(self, enum_type: Type[Enum], **kwargs):
        super().__init__(128, **kwargs)
        if not issubclass(enum_type, Enum):
            raise ConfigurationError(f"{enum_type} is not a subclass of Enum!")
        self.enum_type = enum_type

    def to_db_value(self, value, instance):
        self.validate(value)

        if value is None:
            return None

        if not isinstance(value, self.enum_type):
            raise TypeError(f"Expected type {self.enum_type}, got {value}")

        return value.value

    def to_python_value(self, value):
        if value is None or isinstance(value, self.enum_type):
            return value

        try:
            return self.enum_type(value)
        except ValueError:
            raise ValueError(f"Database value {value} does not exist on Enum {self.enum_type}.")


class IntEnumField(IntField):
    """
    An example extension to CharField that serializes Enums
    to and from a Text representation in the DB.
    """

    __slots__ = ("enum_type",)

    def __init__(self, enum_type: Type[IntEnum], **kwargs):
        super().__init__(**kwargs)
        if not issubclass(enum_type, IntEnum):
            raise ConfigurationError(f"{enum_type} is not a subclass of IntEnum!")
        self.enum_type = enum_type

    def to_db_value(self, value: Any, instance) -> Any:
        self.validate(value)

        if value is None:
            return value
        if not isinstance(value, self.enum_type):
            raise TypeError(f"Expected type {self.enum_type}, got {value}")

        return value.value

    def to_python_value(self, value: Any) -> Any:
        if value is None or isinstance(value, self.enum_type):
            return value

        try:
            return self.enum_type(value)
        except ValueError:
            raise ValueError(f"Database value {value} does not exist on Enum {self.enum_type}.")
