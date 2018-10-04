from typing import List

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


class MySQLExecutor(BaseExecutor):
    FILTER_FUNC_OVERRIDE = {
        contains: mysql_contains,
        starts_with: mysql_starts_with,
        ends_with: mysql_ends_with,
        insensitive_contains: mysql_insensitive_contains,
        insensitive_starts_with: mysql_insensitive_starts_with,
        insensitive_ends_with: mysql_insensitive_ends_with
    }

    def _prepare_insert_statement(self, columns: List[str]) -> str:
        return str(
            MySQLQuery.into(Table(self.model._meta.table)).columns(*columns)
            .insert('???')
        ).replace("'???'", ','.join(['%s' for _ in range(len(columns))]))
