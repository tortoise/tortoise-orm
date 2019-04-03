from typing import Optional, Union
from uuid import UUID

from tortoise.fields import JSONField as GenericJSONField, UUIDField as GenericUUIDField


class JSONField(GenericJSONField):
    def to_db_value(self, value: Optional[Union[dict, list]], instance):
        return value

    def to_python_value(self, value: Optional[Union[str, dict, list]]):
        return value


class UUIDField(GenericUUIDField):
    def to_db_value(self, value: Optional[UUID], instance):
        return value

    def to_python_value(self, value: Optional[UUID]):
        return value
