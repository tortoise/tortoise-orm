from decimal import Decimal

from pypika import Table

from tortoise import fields
from tortoise.backends.base.executor import BaseExecutor


def to_db_bool(self, value):
    if value is None:
        return None
    if bool(value):
        return 1
    else:
        return 0


def to_db_decimal(self, value):
    if value is None:
        return None
    # TODO: quantize step only needed for SQLite
    if self.decimal_places == 0:
        quant = '1'
    else:
        quant = '1.{}'.format('0' * self.decimal_places)
    return Decimal(value).quantize(Decimal(quant)).normalize()


TO_DB_OVERRIDE = {
    fields.BooleanField: to_db_bool,
    fields.DecimalField: to_db_decimal,
}


class SqliteExecutor(BaseExecutor):
    async def execute_insert(self, instance):
        self.connection = await self.db.get_single_connection()
        regular_columns, generated_column_pairs = self._prepare_insert_columns()
        columns, values = self._prepare_insert_values(
            instance=instance,
            regular_columns=regular_columns,
            generated_column_pairs=generated_column_pairs,
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

    def _get_prepared_value(self, instance, column):
        field_object = self.model._meta.fields_map[column]
        if field_object.__class__ in TO_DB_OVERRIDE:
            return TO_DB_OVERRIDE[field_object.__class__](field_object, getattr(instance, column))
        return field_object.to_db_value(getattr(instance, column))
