"""Shared quoting and schema-qualification mixins for schema generators and migration editors.

Both ``BaseSchemaGenerator`` (backends) and ``BaseSchemaEditor`` (migrations) need
identical ``quote()`` and ``_qualify_table_name()`` logic per SQL dialect.  These
mixins provide a single source of truth so that each dialect's quoting rules live
in exactly one place.
"""

from __future__ import annotations


class SchemaQuotingMixin:
    """Default quoting using double-quotes (ANSI SQL).

    Used by PostgreSQL and Oracle dialects.
    """

    def quote(self, val: str) -> str:
        return f'"{val}"'

    def _qualify_table_name(self, table_name: str, schema: str | None = None) -> str:
        if schema:
            return f"{self.quote(schema)}.{self.quote(table_name)}"
        return self.quote(table_name)


class MySQLQuotingMixin:
    """MySQL quoting using backticks."""

    @staticmethod
    def quote(val: str) -> str:
        return f"`{val}`"

    def _qualify_table_name(self, table_name: str, schema: str | None = None) -> str:
        if schema:
            return f"`{schema}`.`{table_name}`"
        return f"`{table_name}`"


class MSSQLQuotingMixin:
    """MSSQL quoting using square brackets."""

    @staticmethod
    def quote(val: str) -> str:
        return f"[{val}]"

    def _qualify_table_name(self, table_name: str, schema: str | None = None) -> str:
        if schema:
            return f"[{schema}].[{table_name}]"
        return f"[{table_name}]"


class SqliteQuotingMixin(SchemaQuotingMixin):
    """SQLite quoting — same as ANSI but ignores schema."""

    def _qualify_table_name(self, table_name: str, schema: str | None = None) -> str:
        # SQLite does not support database schemas in the standard sense
        return self.quote(table_name)
