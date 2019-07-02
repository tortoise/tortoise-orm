from typing import List

from tortoise import fields
from tortoise.backends.base.schema_generator import BaseSchemaGenerator


class AsyncpgSchemaGenerator(BaseSchemaGenerator):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.FIELD_TYPE_MAP.update({fields.JSONField: "JSONB", fields.UUIDField: "UUID"})
        self.TABLE_COMMENT_TEMPLATE = "COMMENT ON TABLE {table} IS '{comment}';"
        self.COLUMN_COMMNET_TEMPLATE = "COMMENT ON COLUMN {table}.{column} IS '{comment}';"

    def _get_primary_key_create_string(self, field_name: str) -> str:
        return '"{}" SERIAL NOT NULL PRIMARY KEY'.format(field_name)

    def _table_comment_generator(self, model, comments_array: List) -> str:
        if model._meta.table_description:
            comments_array.append(
                self.TABLE_COMMENT_TEMPLATE.format(
                    table=model._meta.table, comment=model._meta.table_description
                )
            )
        return ""

    def _column_comment_generator(self, model, field, comments_array: List) -> str:
        if field.description:
            comments_array.append(
                self.COLUMN_COMMNET_TEMPLATE.format(
                    table=model._meta.table,
                    column=field.model_field_name,
                    comment=field.description,
                )
            )
        return ""
