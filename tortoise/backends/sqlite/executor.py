from decimal import Decimal

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

    async def execute_insert(self, instance):
        self.connection = await self.db.get_single_connection()
        regular_columns = self._prepare_insert_columns()
        columns, values = self._prepare_insert_values(
            instance=instance,
            regular_columns=regular_columns,
        )

        query = (
            self.connection.query_class.into(Table(self.model._meta.table)).columns(*columns)
            .insert(*values)
        )
        result = await self.connection.execute_query(str(query), get_inserted_id=True)
        instance.id = result[0]
        await self.db.release_single_connection(self.connection)
        self.connection = None
        return instance
