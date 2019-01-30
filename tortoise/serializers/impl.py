from typing import Generic, TypeVar, Type, Union  # noqa

from tortoise.models import Model

from .backends import SerializationBackend, load_serialization_backend
from .base import BaseSerializer
from .datatypes import Data

T = TypeVar('T')


class Serializer(BaseSerializer[T]):  # pylint: disable=unsubscriptable-object
    """A concrete serializer class backed by a serialization backend."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.backend = self._get_backend()

    def _get_backend(self) -> SerializationBackend:
        backend = self._meta.options.get('backend')

        if backend is None:
            raise AssertionError('A value for `backend` should be set in `Meta.options`.')

        if isinstance(backend, str):
            backend = load_serialization_backend(backend)

        return backend(serializer=self, config=self._meta)

    def to_internal_value(self, data: Data) -> Data:
        return self.backend.to_internal_value(data)

    def to_representation(self, instance: T) -> Data:
        return self.backend.to_representation(instance)


class ModelSerializer(Serializer[Model]):
    """A concrete model serializer class."""

    async def perform_create(self, validated_data: Data) -> Model:
        return await self._meta.model.create(**validated_data)

    async def perform_update(self, instance: Model, validated_data: Data) -> Model:
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        await instance.save()
        return instance
