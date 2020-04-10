import datetime
from decimal import Decimal
from typing import Optional, Type, Union

from pypika import Parameter

from tortoise import Model, fields
from tortoise.backends.base.executor import BaseExecutor
from tortoise.fields import (
    BigIntField,
    BooleanField,
    DatetimeField,
    DecimalField,
    IntField,
    SmallIntField,
)


def to_db_bool(
    self: BooleanField, value: Optional[Union[bool, int]], instance: Union[Type[Model], Model]
) -> Optional[int]:
    if value is None:
        return None
    return int(bool(value))


def to_db_decimal(
    self: DecimalField,
    value: Optional[Union[str, float, int, Decimal]],
    instance: Union[Type[Model], Model],
) -> Optional[str]:
    if value is None:
        return None
    return str(Decimal(value).quantize(self.quant).normalize())


def to_db_datetime(
    self: DatetimeField, value: Optional[datetime.datetime], instance: Union[Type[Model], Model]
) -> Optional[str]:
    if hasattr(instance, "_saved_in_db"):
        # Only do this if it is a Model instance, not class. Test for guaranteed instance var
        if self.auto_now or (
            self.auto_now_add and getattr(instance, self.model_field_name, None) is None
        ):
            value = datetime.datetime.utcnow()
            setattr(instance, self.model_field_name, value)
            return value.isoformat(" ")
    if isinstance(value, datetime.datetime):
        return value.isoformat(" ")
    return None


class SqliteExecutor(BaseExecutor):
    TO_DB_OVERRIDE = {
        fields.BooleanField: to_db_bool,
        fields.DecimalField: to_db_decimal,
        fields.DatetimeField: to_db_datetime,
    }
    EXPLAIN_PREFIX = "EXPLAIN QUERY PLAN"
    DB_NATIVE = {bytes, str, int, float}

    def parameter(self, pos: int) -> Parameter:
        return Parameter("?")

    async def _process_insert_result(self, instance: Model, results: int) -> None:
        pk_field_object = self.model._meta.pk
        if (
            isinstance(pk_field_object, (SmallIntField, IntField, BigIntField))
            and pk_field_object.generated
        ):
            instance.pk = results

        # SQLite can only generate a single ROWID
        #   so if any other primary key, it won't generate what we want.
