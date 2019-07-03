from typing import List

from tortoise import fields
from tortoise.backends.base.schema_generator import BaseSchemaGenerator
from tortoise.utils import get_escape_translation_table


class AsyncpgSchemaGenerator(BaseSchemaGenerator):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.FIELD_TYPE_MAP.update({fields.JSONField: "JSONB", fields.UUIDField: "UUID"})
        self.TABLE_COMMENT_TEMPLATE = "COMMENT ON TABLE {table} IS '{comment}';"
        self.COLUMN_COMMNET_TEMPLATE = "COMMENT ON COLUMN {table}.{column} IS '{comment}';"

    def _get_primary_key_create_string(self, field_name: str) -> str:
        return '"{}" SERIAL NOT NULL PRIMARY KEY'.format(field_name)

    def _escape_comment(self, comment: str) -> str:
        table = get_escape_translation_table()
        table[ord("'")] = u"''"
        return comment.translate(table)

    def _table_comment_generator(self, model, comments_array: List) -> str:
        if model._meta.table_description:
            comment = self.TABLE_COMMENT_TEMPLATE.format(
                table=model._meta.table,
                comment=self._escape_comment(comment=model._meta.table_description),
            )
            comments_array.append(comment)
        return ""

    def _column_comment_generator(self, model, field, comments_array: List) -> str:
        if field.description:
            comment = self.COLUMN_COMMNET_TEMPLATE.format(
                table=model._meta.table,
                column=field.model_field_name,
                comment=self._escape_comment(field.description),
            )
            comments_array.append(comment)
        return ""

    def _post_table_hook(self, *, models=None, safe=True) -> str:
        table_comments = []  # type: List[str]
        column_comments = []  # type: List[str]
        for model in models:
            self._table_comment_generator(model=model, comments_array=table_comments)
            for field_name, _ in model._meta.fields_db_projection.items():
                field_object = model._meta.fields_map[field_name]
                self._column_comment_generator(
                    model=model, field=field_object, comments_array=column_comments
                )
        return " ".join(table_comments + column_comments)
