from pypika import Parameter, functions
from pypika.enums import SqlTypes
from pypika.terms import Criterion

from tortoise import Model
from tortoise.backends.base.executor import BaseExecutor
from tortoise.contrib.mysql.search import SearchCriterion
from tortoise.fields import BigIntField, IntField, SmallIntField
from tortoise.filters import (
    Like,
    Term,
    ValueWrapper,
    contains,
    ends_with,
    format_quotes,
    insensitive_contains,
    insensitive_ends_with,
    insensitive_exact,
    insensitive_starts_with,
    search,
    starts_with,
)


class StrWrapper(ValueWrapper):  # type: ignore
    """
    Naive str wrapper that doesn't use the monkey-patched pypika ValueWraper for MySQL
    """

    def get_value_sql(self, **kwargs):
        quote_char = kwargs.get("secondary_quote_char") or ""
        value = self.value.replace(quote_char, quote_char * 2)
        return format_quotes(value, quote_char)


def escape_like(val: str) -> str:
    return val.replace("\\", "\\\\\\\\").replace("%", "\\%").replace("_", "\\_")


def mysql_contains(field: Term, value: str) -> Criterion:
    return Like(
        functions.Cast(field, SqlTypes.CHAR), StrWrapper(f"%{escape_like(value)}%"), escape=""
    )


def mysql_starts_with(field: Term, value: str) -> Criterion:
    return Like(
        functions.Cast(field, SqlTypes.CHAR), StrWrapper(f"{escape_like(value)}%"), escape=""
    )


def mysql_ends_with(field: Term, value: str) -> Criterion:
    return Like(
        functions.Cast(field, SqlTypes.CHAR), StrWrapper(f"%{escape_like(value)}"), escape=""
    )


def mysql_insensitive_exact(field: Term, value: str) -> Criterion:
    return functions.Upper(functions.Cast(field, SqlTypes.CHAR)).eq(functions.Upper(str(value)))


def mysql_insensitive_contains(field: Term, value: str) -> Criterion:
    return Like(
        functions.Upper(functions.Cast(field, SqlTypes.CHAR)),
        functions.Upper(StrWrapper(f"%{escape_like(value)}%")),
        escape="",
    )


def mysql_insensitive_starts_with(field: Term, value: str) -> Criterion:
    return Like(
        functions.Upper(functions.Cast(field, SqlTypes.CHAR)),
        functions.Upper(StrWrapper(f"{escape_like(value)}%")),
        escape="",
    )


def mysql_insensitive_ends_with(field: Term, value: str) -> Criterion:
    return Like(
        functions.Upper(functions.Cast(field, SqlTypes.CHAR)),
        functions.Upper(StrWrapper(f"%{escape_like(value)}")),
        escape="",
    )


def mysql_search(field: Term, value: str):
    return SearchCriterion(field, expr=StrWrapper(value))


class MySQLExecutor(BaseExecutor):
    FILTER_FUNC_OVERRIDE = {
        contains: mysql_contains,
        starts_with: mysql_starts_with,
        ends_with: mysql_ends_with,
        insensitive_exact: mysql_insensitive_exact,
        insensitive_contains: mysql_insensitive_contains,
        insensitive_starts_with: mysql_insensitive_starts_with,
        insensitive_ends_with: mysql_insensitive_ends_with,
        search: mysql_search,
    }
    EXPLAIN_PREFIX = "EXPLAIN FORMAT=JSON"

    def parameter(self, pos: int) -> Parameter:
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
