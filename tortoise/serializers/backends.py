from importlib import import_module
from typing import Any, Set, Type

from .datatypes import Data
from .exceptions import MissingDependencies
from .meta import MetaInfo


class SerializationBackend:
    """Base serialization backend class."""

    def __init__(self, serializer, config: MetaInfo):
        self.serializer = serializer
        self.config = config

    def get_declared_fields(self) -> Set[str]:
        return self.config.fields

    def get_excluded_fields(self) -> Set[str]:
        return self.config.exclude

    def get_field_names(self) -> Set[str]:
        return self.get_declared_fields().difference(self.get_excluded_fields())

    def to_internal_value(self, data: Data) -> Data:
        raise NotImplementedError

    def to_representation(self, instance: Any) -> Data:
        raise NotImplementedError


def load_serialization_backend(name: str) -> Type[SerializationBackend]:
    try:
        module = import_module('tortoise.contrib.{}'.format(name))  # type: Any
    except MissingDependencies as exc:
        raise ImportError(
            'Backend "{}" found, but some dependencies are missing: {}.'
            .format(name, ', '.join(exc.dependencies))
        ) from exc
    except ImportError as exc:
        raise ImportError('Backend "{}" does not exist.'.format(name)) from exc

    return module.backend
