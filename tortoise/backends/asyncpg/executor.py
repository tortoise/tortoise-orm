from pypika import Table

from tortoise.backends.base.executor import BaseExecutor


class AsyncpgExecutor(BaseExecutor):
    async def execute_insert(self, instance):
        self.connection = await self.db.get_single_connection()
        columns = list(self.model._meta.fields_db_projection.values())
        columns = [c for c in columns if not self.model._meta.fields_map[c].generated]
        values = [
            getattr(instance, self.model._meta.fields_db_projection_reverse[column])
            for column in columns
        ]
        query = (
            self.connection.query_class.into(Table(self.model._meta.table))
            .columns(*columns)
            .insert(*values)
            .returning('id')
        )
        result = await self.connection.execute_query(str(query))
        instance.id = result[0][0]
        await self.db.release_single_connection(self.connection)
        self.connection = None
        return instance
