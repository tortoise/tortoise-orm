from typing import Any, List

from pymysql.converters import encoders

from tortoise.backends.base.schema_generator import BaseSchemaGenerator


class SqliteSchemaGenerator(BaseSchemaGenerator):
    DIALECT = "sqlite"

    @classmethod
    def _get_escape_translation_table(cls) -> List[str]:
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
        auto_now_add: bool = False,
        auto_now: bool = False,
    ) -> str:
        default_str = " DEFAULT"
        if auto_now_add:
            default_str += " CURRENT_TIMESTAMP"
        else:
            default_str += f" {default}"
        return default_str

    def _escape_default_value(self, default: Any):
        return encoders.get(type(default))(default)
