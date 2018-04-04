import datetime
from pypika import Table

from tortoise import fields
from tortoise.backends.base.executor import BaseExecutor


class AsyncpgExecutor(BaseExecutor):
    async def execute_insert(self, instance):
        self.connection = await self.db.get_single_connection()
        columns = list(self.model._meta.fields_db_projection.values())
        columns_filtered = []
        python_generated_columns = []
        now = datetime.datetime.utcnow()
        for column in columns:
            field_object = self.model._meta.fields_map[column]
            if isinstance(field_object, fields.DatetimeField) and field_object.auto_now_add:
                python_generated_columns.append((column, now))
            elif field_object.generated:
                continue
            else:
                columns_filtered.append(column)
        values = [
            getattr(instance, self.model._meta.fields_db_projection_reverse[column])
            for column in columns_filtered
        ]
        for column, value in python_generated_columns:
            columns_filtered.append(column)
            values.append(value)
            setattr(instance, column, value)
        query = (
            self.connection.query_class.into(Table(self.model._meta.table))
            .columns(*columns_filtered)
            .insert(*values)
            .returning('id')
        )
        result = await self.connection.execute_query(str(query))
        instance.id = result[0][0]
        await self.db.release_single_connection(self.connection)
        self.connection = None
        return instance
