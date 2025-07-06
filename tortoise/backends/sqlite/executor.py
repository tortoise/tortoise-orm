import datetime
import re
import sqlite3
from decimal import Decimal

from pypika_tortoise.enums import SqlTypes
from pypika_tortoise.functions import Cast, Upper
from pypika_tortoise.terms import (
    Criterion,
    Term,
)

from tortoise import Model
from tortoise.backends.base.executor import BaseExecutor
from tortoise.contrib.sqlite.regex import (
    insensitive_posix_sqlite_regexp,
    posix_sqlite_regexp,
)
from tortoise.fields import BigIntField, IntField, SmallIntField
from tortoise.filters import Like, insensitive_posix_regex, posix_regex

# Conversion for the cases where it's hard to know the
# related field, e.g. in raw queries, math or annotations.
sqlite3.register_adapter(Decimal, str)
sqlite3.register_adapter(datetime.date, lambda val: val.isoformat())
sqlite3.register_adapter(datetime.datetime, lambda val: val.isoformat(" "))


def escape_backslash_except_wildcards(val: str) -> str:
    # Replace \ with \\ if the backslash is not followed by % or _
    return re.sub(r"\\(?![%_])", r"\\", val)


def like(field: Term, value: str) -> Criterion:
    return Like(
        Cast(field, SqlTypes.VARCHAR),
        field.wrap_constant(escape_backslash_except_wildcards(value)),
    )


def ilike(field: Term, value: str) -> Criterion:
    return Like(
        Upper(Cast(field, SqlTypes.VARCHAR)),
        field.wrap_constant(Upper(escape_backslash_except_wildcards(value))),
    )


class SqliteExecutor(BaseExecutor):
    EXPLAIN_PREFIX = "EXPLAIN QUERY PLAN"
    DB_NATIVE = {bytes, str, int, float}
    FILTER_FUNC_OVERRIDE = {
        posix_regex: posix_sqlite_regexp,
        insensitive_posix_regex: insensitive_posix_sqlite_regexp,
        like: like,
        ilike: ilike,
    }

    async def _process_insert_result(self, instance: Model, results: int) -> None:
        pk_field_object = self.model._meta.pk
        if (
            isinstance(pk_field_object, (SmallIntField, IntField, BigIntField))
            and pk_field_object.generated
        ):
            instance.pk = results

        # SQLite can only generate a single ROWID
        #   so if any other primary key, it won't generate what we want.
