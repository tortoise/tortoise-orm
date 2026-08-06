from __future__ import annotations

from typing import Any

from tortoise.backends.base.schema_generator import BaseSchemaGenerator
from tortoise.converters import encoders
from tortoise.schema_quoting import SqliteQuotingMixin


class SqliteSchemaGenerator(SqliteQuotingMixin, BaseSchemaGenerator):
    DIALECT = "sqlite"

    @classmethod
    def _get_escape_translation_table(cls) -> list[str]:
        table = super()._get_escape_translation_table()
        table[ord('"')] = '"'
        table[ord("'")] = "'"
        table[ord("/")] = "\\/"
        return table

    def _table_comment_generator(self, table: str, comment: str) -> str:
        return f" /* {self._escape_comment(comment)} */"

    def _column_comment_generator(self, table: str, column: str, comment: str) -> str:
        return f" /* {self._escape_comment(comment)} */"

    def _column_default_generator(
        self,
        table: str,
        column: str,
        default: Any,
    ) -> str:
        return f" DEFAULT {default}"

    def _escape_default_value(self, default: Any):
        return encoders.get(type(default))(default)  # type: ignore
