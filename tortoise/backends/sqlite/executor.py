import datetime
from pypika import Table

from tortoise import fields
from tortoise.backends.base.executor import BaseExecutor


class SqliteExecutor(BaseExecutor):
    async def execute_insert(self, instance):
        self.connection = await self.db.get_single_connection()
        columns, generated_columns = self._prepare_insert_columns()
        values = self._prepare_insert_values(instance, columns, generated_columns)

        query = (
            self.connection.query_class.into(Table(self.model._meta.table))
            .columns(*columns)
            .insert(*values)
        )
        result = await self.connection.execute_query(str(query), get_inserted_id=True)
        instance.id = result[0]
        await self.db.release_single_connection(self.connection)
        self.connection = None
        return instance
