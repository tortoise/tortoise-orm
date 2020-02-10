from pypika import Parameter, functions
from pypika.enums import SqlTypes
from pypika.terms import Criterion

from tortoise import Model
from tortoise.backends.base.executor import BaseExecutor
from tortoise.fields import BigIntField, Field, IntField, SmallIntField
from tortoise.filters import (
    contains,
    ends_with,
    insensitive_contains,
    insensitive_ends_with,
    insensitive_exact,
    insensitive_starts_with,
    starts_with,
)


def mysql_contains(field: Field, value: str) -> Criterion:
    return functions.Cast(field, SqlTypes.CHAR).like(f"%{value}%")


def mysql_starts_with(field: Field, value: str) -> Criterion:
    return functions.Cast(field, SqlTypes.CHAR).like(f"{value}%")


def mysql_ends_with(field: Field, value: str) -> Criterion:
    return functions.Cast(field, SqlTypes.CHAR).like(f"%{value}")


def mysql_insensitive_exact(field: Field, value: str) -> Criterion:
    return functions.Upper(functions.Cast(field, SqlTypes.CHAR)).eq(functions.Upper(f"{value}"))


def mysql_insensitive_contains(field: Field, value: str) -> Criterion:
    return functions.Upper(functions.Cast(field, SqlTypes.CHAR)).like(functions.Upper(f"%{value}%"))


def mysql_insensitive_starts_with(field: Field, value: str) -> Criterion:
    return functions.Upper(functions.Cast(field, SqlTypes.CHAR)).like(functions.Upper(f"{value}%"))


def mysql_insensitive_ends_with(field: Field, value: str) -> Criterion:
    return functions.Upper(functions.Cast(field, SqlTypes.CHAR)).like(functions.Upper(f"%{value}"))


class MySQLExecutor(BaseExecutor):
    FILTER_FUNC_OVERRIDE = {
        contains: mysql_contains,
        starts_with: mysql_starts_with,
        ends_with: mysql_ends_with,
        insensitive_exact: mysql_insensitive_exact,
        insensitive_contains: mysql_insensitive_contains,
        insensitive_starts_with: mysql_insensitive_starts_with,
        insensitive_ends_with: mysql_insensitive_ends_with,
    }
    EXPLAIN_PREFIX = "EXPLAIN FORMAT=JSON"

    def Parameter(self, pos: int) -> Parameter:
        return Parameter("%s")

    async def _process_insert_result(self, instance: Model, results: int) -> None:
        pk_field_object = self.model._meta.pk
        if (
            isinstance(pk_field_object, (SmallIntField, IntField, BigIntField))
            and pk_field_object.generated
        ):
            instance.pk = results

        # MySQL can only generate a single ROWID
        #   so if any other primary key, it won't generate what we want.
