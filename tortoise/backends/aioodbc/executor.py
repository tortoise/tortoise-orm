from pypika import Parameter, functions
from pypika.terms import Criterion, Field

from tortoise import Model
from tortoise.backends.base.executor import BaseExecutor
from tortoise.fields import BigIntField, IntField, SmallIntField
from tortoise.filters import (
    contains,
    ends_with,
    insensitive_contains,
    insensitive_ends_with,
    insensitive_exact,
    insensitive_starts_with,
    starts_with,
)


def aiodbc_contains(field: Field, value: str) -> Criterion:
    return field.like(f"%{value}%")


def aiodbc_starts_with(field: Field, value: str) -> Criterion:
    return field.like(f"{value}%")


def aiodbc_ends_with(field: Field, value: str) -> Criterion:
    return field.like(f"%{value}")


def aiodbc_insensitive_exact(field: Field, value: str) -> Criterion:
    return functions.Upper(field).eq(functions.Upper(f"{value}"))


def aiodbc_insensitive_contains(field: Field, value: str) -> Criterion:
    return functions.Upper(field).like(functions.Upper(f"%{value}%"))


def aiodbc_insensitive_starts_with(field: Field, value: str) -> Criterion:
    return functions.Upper(field).like(functions.Upper(f"{value}%"))


def aiodbc_insensitive_ends_with(field: Field, value: str) -> Criterion:
    return functions.Upper(field).like(functions.Upper(f"%{value}"))


class AioodbcExecutor(BaseExecutor):
    FILTER_FUNC_OVERRIDE = {
        contains: aiodbc_contains,
        starts_with: aiodbc_starts_with,
        ends_with: aiodbc_ends_with,
        insensitive_exact: aiodbc_insensitive_exact,
        insensitive_contains: aiodbc_insensitive_contains,
        insensitive_starts_with: aiodbc_insensitive_starts_with,
        insensitive_ends_with: aiodbc_insensitive_ends_with,
    }
    EXPLAIN_PREFIX = "EXPLAIN FORMAT=JSON"

    def parameter(self, pos: int) -> Parameter:
        return Parameter(f":{pos}")

    async def _process_insert_result(self, instance: Model, results: int) -> None:
        pk_field_object = self.model._meta.pk
        if (
            isinstance(pk_field_object, (SmallIntField, IntField, BigIntField))
            and pk_field_object.generated
        ):
            instance.pk = results
