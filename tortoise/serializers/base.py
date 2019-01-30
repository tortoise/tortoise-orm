from typing import Generic, TypeVar

from .datatypes import Data
from .exceptions import ValidationError
from .meta import MetaInfo

T = TypeVar('T')


class BaseSerializerMeta(type):

    def __new__(mcs, name: str, bases: tuple, attrs: dict):
        attrs["_meta"] = MetaInfo(attrs.get("Meta"))
        return super().__new__(mcs, name, bases, attrs)


class BaseSerializer(Generic[T], metaclass=BaseSerializerMeta):

    # Fix for autocompletion / static analysis.
    _meta = MetaInfo(None)

    def to_internal_value(self, data: Data) -> Data:
        raise NotImplementedError

    def to_representation(self, instance: T) -> Data:
        raise NotImplementedError

    def validate(self, data: Data) -> Data:
        try:
            validated_data = self.to_internal_value(data)
        except ValidationError as exc:
            raise exc from None
        else:
            return validated_data

    def dump(self, instance: T) -> Data:
        return self.to_representation(instance)

    async def perform_create(self, validated_data: Data) -> T:
        raise NotImplementedError

    async def perform_update(self, instance: T, validated_data: Data) -> T:
        raise NotImplementedError

    async def create(self, data: Data) -> T:
        validated_data = self.validate(data)
        return await self.perform_create(validated_data)

    async def update(self, instance: T, data: Data) -> T:
        validated_data = self.validate(data)
        return await self.perform_update(instance, validated_data)
