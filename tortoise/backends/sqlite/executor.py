from decimal import Decimal
from typing import List

from pypika import Table

from tortoise import fields
from tortoise.backends.base.executor import BaseExecutor


def to_db_bool(self, value, instance):
    if value is None:
        return None
    return int(bool(value))


def to_db_decimal(self, value, instance):
    if value is None:
        return None
    if self.decimal_places == 0:
        quant = '1'
    else:
        quant = '1.{}'.format('0' * self.decimal_places)
    return str(Decimal(value).quantize(Decimal(quant)).normalize())


class SqliteExecutor(BaseExecutor):
    TO_DB_OVERRIDE = {
        fields.BooleanField: to_db_bool,
        fields.DecimalField: to_db_decimal,
    }

    def _prepare_insert_statement(self, columns: List[str]) -> str:
        return str(
            self.connection.query_class.into(Table(self.model._meta.table)).columns(*columns)
            .insert('???')
        ).replace("'???'", ','.join(['?' for _ in range(len(columns))]))
