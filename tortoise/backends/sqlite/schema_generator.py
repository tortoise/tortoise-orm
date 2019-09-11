from typing import Optional

from tortoise import fields
from tortoise.backends.base.schema_generator import BaseSchemaGenerator


class SqliteSchemaGenerator(BaseSchemaGenerator):
    FIELD_TYPE_MAP = {
        **BaseSchemaGenerator.FIELD_TYPE_MAP,
        fields.BooleanField: "INTEGER",
        fields.FloatField: "REAL",
        fields.DecimalField: "VARCHAR(40)",
    }

    def _escape_comment(self, comment: str) -> str:  # pylint: disable=R0201
        # This method provides a default method to escape comment strings as per
        # default standard as applied under mysql like database. This can be
        # overwritten if required to match the database specific escaping.
        _escape_table = [chr(x) for x in range(128)]
        _escape_table[0] = "\\0"
        _escape_table[ord("\\")] = "\\\\"
        _escape_table[ord("\n")] = "\\n"
        _escape_table[ord("\r")] = "\\r"
        _escape_table[ord("\032")] = "\\Z"
        _escape_table[ord("/")] = "\\/"
        return comment.translate(_escape_table)

    def _get_primary_key_create_string(
        self, field_object: fields.Field, field_name: str, comment: str
    ) -> Optional[str]:
        if isinstance(field_object, (fields.SmallIntField, fields.IntField, fields.BigIntField)):
            return f'"{field_name}" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL{comment}'
        return None

    def _table_comment_generator(self, table: str, comment: str) -> str:
        return f" /* {self._escape_comment(comment)} */"

    def _column_comment_generator(self, table: str, column: str, comment: str) -> str:
        return f" /* {self._escape_comment(comment)} */"
