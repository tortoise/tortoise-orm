from __future__ import annotations

import re
from typing import Any

from pypika_tortoise.enums import SqlTypes
from pypika_tortoise.functions import Cast, Upper
from pypika_tortoise.terms import Criterion, Term, Function as PypikaFunction

from tortoise.backends.odbc.executor import ODBCExecutor
from tortoise.exceptions import UnSupportedError
from tortoise.filters import Like, like, ilike


def escape_backslash_except_wildcards(val: str) -> str:
    # Replace \ with \\\\ if the backslash is not followed by % or _
    return re.sub(r"\\(?![%_])", "\\\\\\\\", val)


class collateFunction(PypikaFunction):
    """
    Custom function to apply collation in SQL Server
    """
    def __init__(self, field: Term, collation: str) -> None:
        super().__init__("COLLATE", field, collation)
        self.collation_name = collation
    
    def get_sql(self, ctx):
        field_sql = self.args[0].get_sql(ctx)
        return f"{field_sql} COLLATE {self.collation_name}"


def mssql_like(field: Term, value: str) -> Criterion:
    # For SQL Server, we need to use a case-sensitive collation to force case sensitive LIKE.
    # Latin1_General_CS_AS is a common case-sensitive collation.
    # We apply the collation directly to the field without casting to preserve escaping behavior.
    escaped = escape_backslash_except_wildcards(value)
    return Like(
        collateFunction(field, "Latin1_General_CS_AS"),
        field.wrap_constant(escaped),
    )

def mssql_ilike(field: Term, value: str) -> Criterion:
    return Like(
        Upper(Cast(field, SqlTypes.VARCHAR)),
        field.wrap_constant(Upper(escape_backslash_except_wildcards(value))),
    )

class MSSQLExecutor(ODBCExecutor):
    FILTER_FUNC_OVERRIDE = {like: mssql_like, ilike: mssql_ilike}

    async def execute_explain(self, sql: str) -> Any:
        raise UnSupportedError("MSSQL does not support explain")
