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
        self.TABLE_CREATE_TEMPLATE = 'CREATE TABLE {exists}"{table_name}" {comment} ({fields});'

    def _get_primary_key_create_string(self, field_name: str) -> str:
        return '"{}" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL'.format(field_name)

    def _table_comment_generator(self, model, comments_array: List) -> str:
        comment = ""
        if model._meta.table_description:
            comment = "{}".format(model._meta.table_description)

        return " ".join(["/*", self._escape_comment(comment=comment), "*/"]) if comment else ""

    def _column_comment_generator(self, model, field, comments_array: List) -> str:
        comment = ""
        if field.description:
            comment = "{}".format(field.description)

        return " ".join(["/*", self._escape_comment(comment=comment), "*/"]) if comment else ""
