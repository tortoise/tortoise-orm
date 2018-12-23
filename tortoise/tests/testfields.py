from enum import Enum
from typing import Type

from tortoise import ConfigurationError
from tortoise.fields import CharField


class EnumField(CharField):
    """
    An example extension to CharField that serializes Enums
    to and from a Text representation in the DB.
    """

    def __init__(self, enum_type: Type[Enum], **kwargs):
        super().__init__(128, **kwargs)
        if not issubclass(enum_type, Enum):
            raise ConfigurationError("{} is not a subclass of Enum!".format(enum_type))
        self._enum_type = enum_type

    def to_db_value(self, value, instance):
        if isinstance(value, self._enum_type):
            return value.value

        return value

    def to_python_value(self, value):
        try:
            return self._enum_type(value)
        except ValueError:
            if not self.null:
                raise ValueError(
                    "Database value {} does not exist on Enum {}.".format(value, self._enum_type)
                )

            return None
