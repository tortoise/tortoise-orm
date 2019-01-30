import datetime
import decimal
import json
from typing import Any, Dict, Optional, Set, TypeVar, Tuple, Type, Union  # noqa

from tortoise import fields
from tortoise.fields import Field
from tortoise.serializers.backends import SerializationBackend
from tortoise.serializers.datatypes import Data
from tortoise.serializers.exceptions import ValidationError
from tortoise.serializers.field_utils import is_read_only

try:
    from pydantic import BaseModel, ValidationError as PydanticValidationError, create_model
except ImportError as exc:
    raise exc from None

T = TypeVar('T')
Definition = Union[Any, Tuple[Type, Any]]


_FIELD_TO_PYDANTIC_TYPE = {
    fields.IntField: int,
    fields.BigIntField: int,
    fields.SmallIntField: int,
    fields.CharField: str,
    fields.TextField: str,
    fields.BooleanField: bool,
    fields.DecimalField: decimal.Decimal,
    fields.DatetimeField: datetime.datetime,
    fields.DateField: datetime.date,
    fields.TimeDeltaField: datetime.timedelta,
    fields.FloatField: float,
    fields.JSONField: Union[dict, list],
}

_REQUIRED = ...


class Ignore(Exception):
    pass


class PydanticSerializationBackend(SerializationBackend):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._read_schema: Optional[Type[BaseModel]] = None
        self._write_schema: Optional[Type[BaseModel]] = None

    def _get_schema(self, operation: str, instance: Optional[T] = None) -> Type[BaseModel]:
        """Create a Pydantic model for the given serialization operation."""
        definitions: Dict[str, Definition] = {}

        for field_name in self.get_field_names():
            try:
                definition = self.build_field(field_name, operation, instance=instance)
            except Ignore:
                pass
            else:
                definitions[field_name] = definition

        return create_model(self.config.model.__name__, **definitions)

    def get_field_names(self) -> Set[str]:
        return (
            super().get_field_names()
            .union(set(getattr(self.serializer, '__annotations__', [])))
        )

    def build_field(
        self, field_name: str, operation: str, instance: Optional[T] = None
    ) -> Optional[Definition]:
        try:
            field: Field = self.config.model._meta.fields_map[field_name]
        except KeyError:
            # Treat as a read-only property.
            if operation == 'write':
                raise Ignore
            return getattr(instance, field_name)
        else:
            # Tortoise field
            if operation == 'write' and is_read_only(field):
                raise Ignore

            write_only = False  # Not implemented yet
            if operation == 'read' and write_only:
                raise Ignore

            type_ = _FIELD_TO_PYDANTIC_TYPE[field.__class__]
            value = _REQUIRED  # type: Union[None, ellipsis, Any]

            if field.default is None and field.null:
                value = None
            elif field.default is not None:
                if callable(field.default):
                    raise AssertionError('Callable default values are not supported yet.')
                value = field.default

            return (type_, value)

    def to_internal_value(self, data: Data) -> Data:
        schema = self._get_schema('write')
        try:
            obj = schema(**data)
        except PydanticValidationError as exc:
            raise ValidationError(exc.raw_errors) from exc
        else:
            return obj.dict()

    def to_representation(self, instance: T) -> Data:
        schema = self._get_schema('read', instance=instance)
        data = {
            attr: getattr(instance, attr)
            for attr in schema.__fields__.keys()
        }
        return json.loads(schema(**data).json())


backend = PydanticSerializationBackend
