from __future__ import annotations

import re
from typing import TYPE_CHECKING, cast

from pypika_tortoise.enums import SqlTypes
from pypika_tortoise.functions import Cast, Upper
from pypika_tortoise.terms import (
    Criterion,
    Term,
)

from tortoise import Model
from tortoise.backends.odbc.executor import ODBCExecutor
from tortoise.filters import Like

if TYPE_CHECKING:
    from .client import OracleClient  # pylint: disable=W0611


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


class OracleExecutor(ODBCExecutor):
    FILTER_FUNC_OVERRIDE = {like: like, ilike: ilike}

    async def _process_insert_result(self, instance: Model, results: int) -> None:
        sql = "SELECT SEQUENCE_NAME FROM ALL_TAB_IDENTITY_COLS where TABLE_NAME = ? and OWNER = ?"
        db = cast("OracleClient", self.db)
        ret = await db.execute_query_dict(sql, values=[instance._meta.db_table, db.database])
        try:
            seq = ret[0]["SEQUENCE_NAME"]
        except IndexError:
            return
        sql = f"SELECT {seq}.CURRVAL FROM DUAL"  # nosec:B608
        ret = await db.execute_query_dict(sql)
        await super()._process_insert_result(instance, ret[0]["CURRVAL"])
