from typing import List

from tortoise import fields
from tortoise.backends.base.schema_generator import BaseSchemaGenerator


class SqliteSchemaGenerator(BaseSchemaGenerator):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.FIELD_TYPE_MAP.update(
            {
                fields.BooleanField: "INTEGER",
                fields.FloatField: "REAL",
                fields.DecimalField: "VARCHAR(40)",
            }
        )

    def _get_primary_key_create_string(self, field_name: str) -> str:
        return '"{}" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL'.format(field_name)

    def _table_comment_generator(self, model, comments_array: List) -> str:
        return ""

    def _column_comment_generator(self, model, field, comments_array: List) -> str:
        return ""
