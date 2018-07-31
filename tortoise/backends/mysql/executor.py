from pypika import MySQLQuery, Table, functions
from pypika.enums import SqlTypes

from tortoise.backends.base.executor import BaseExecutor
from tortoise.models import (contains, ends_with, insensitive_contains, insensitive_ends_with,
                             insensitive_starts_with, starts_with)


def mysql_contains(field, value):
    return functions.Cast(field, SqlTypes.CHAR).like('%{}%'.format(value))


def mysql_starts_with(field, value):
    return functions.Cast(field, SqlTypes.CHAR).like('{}%'.format(value))


def mysql_ends_with(field, value):
    return functions.Cast(field, SqlTypes.CHAR).like('%{}'.format(value))


def mysql_insensitive_contains(field, value):
    return functions.Upper(functions.Cast(field, SqlTypes.CHAR)).like(
        functions.Upper('%{}%'.format(value))
    )


def mysql_insensitive_starts_with(field, value):
    return functions.Upper(functions.Cast(field, SqlTypes.CHAR)).like(
        functions.Upper('{}%'.format(value))
    )


def mysql_insensitive_ends_with(field, value):
    return functions.Upper(functions.Cast(field, SqlTypes.CHAR)).like(
        functions.Upper('%{}'.format(value))
    )


FILTER_FUNC_OVERRIDE = {
    contains: mysql_contains,
    starts_with: mysql_starts_with,
    ends_with: mysql_ends_with,
    insensitive_contains: mysql_insensitive_contains,
    insensitive_starts_with: mysql_insensitive_starts_with,
    insensitive_ends_with: mysql_insensitive_ends_with
}


class MySQLExecutor(BaseExecutor):
    async def execute_insert(self, instance):
        self.connection = await self.db.get_single_connection()
        regular_columns, generated_column_pairs = self._prepare_insert_columns()
        columns, values = self._prepare_insert_values(
            instance=instance,
            regular_columns=regular_columns,
            generated_column_pairs=generated_column_pairs,
        )

        query = (
            MySQLQuery.into(Table(self.model._meta.table)).columns(*columns)
            .insert(*values)
        )

        instance.id = await self.connection.execute_query(str(query), get_inserted_id=True)
        await self.db.release_single_connection(self.connection)
        self.connection = None
        return instance

    @staticmethod
    def get_overridden_filter_func(filter_func):
        return FILTER_FUNC_OVERRIDE.get(filter_func)
