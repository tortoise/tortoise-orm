import datetime
from decimal import Decimal
from typing import List, Optional

from pypika import Parameter, Table

from tortoise import Model, fields
from tortoise.backends.base.executor import BaseExecutor
from tortoise.fields import BigIntField, IntField


def to_db_bool(self, value, instance) -> Optional[int]:
    if value is None:
        return None
    return int(bool(value))


def to_db_decimal(self, value, instance) -> Optional[str]:
    if value is None:
        return None
    if self.decimal_places == 0:
        quant = "1"
    else:
        quant = "1.{}".format("0" * self.decimal_places)
    return str(Decimal(value).quantize(Decimal(quant)).normalize())


def to_db_datetime(self, value: Optional[datetime.datetime], instance) -> Optional[str]:
    if self.auto_now:
        value = datetime.datetime.utcnow()
        setattr(instance, self.model_field_name, value)
        return value.isoformat(" ")
    if self.auto_now_add and getattr(instance, self.model_field_name) is None:
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

    def _prepare_insert_statement(self, columns: List[str]) -> str:
        return str(
            self.db.query_class.into(Table(self.model._meta.table))
            .columns(*columns)
            .insert(*[Parameter("?") for _ in range(len(columns))])
        )

    async def _process_insert_result(self, instance: Model, results: int):
        pk_field_object = self.model._meta.pk
        if isinstance(pk_field_object, (IntField, BigIntField)) and pk_field_object.generated:
            instance.pk = results

        # SQLite can only generate a single ROWID
        #   so if any other primary key, it won't generate what we want.
