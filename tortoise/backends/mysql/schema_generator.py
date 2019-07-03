from typing import List

from tortoise import fields
from tortoise.backends.base.schema_generator import BaseSchemaGenerator


class MySQLSchemaGenerator(BaseSchemaGenerator):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.TABLE_CREATE_TEMPLATE = "CREATE TABLE {exists}`{table_name}` ({fields}) {comment};"
        self.INDEX_CREATE_TEMPLATE = "CREATE INDEX `{index_name}` ON `{table_name}` ({fields});"
        self.FIELD_TEMPLATE = "`{name}` {type} {nullable} {unique} {comment}"
        self.FK_TEMPLATE = " REFERENCES `{table}` (`id`) ON DELETE {on_delete}"
        self.M2M_TABLE_TEMPLATE = (
            "CREATE TABLE `{table_name}` ("
            "`{backward_key}` {backward_type} NOT NULL REFERENCES `{backward_table}` (`id`)"
            " ON DELETE CASCADE,"
            "`{forward_key}` {forward_type} NOT NULL REFERENCES `{forward_table}` (`id`)"
            " ON DELETE CASCADE"
            ") {comment};"
        )

        self.FIELD_TYPE_MAP.update(
            {
                fields.FloatField: "DOUBLE",
                fields.DatetimeField: "DATETIME(6)",
                fields.TextField: "TEXT",
            }
        )

    def _get_primary_key_create_string(self, field_name: str) -> str:
        return "`{}` INT UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT".format(field_name)

    def _table_comment_generator(self, model, comments_array=None) -> str:
        comment = ""
        if model._meta.table_description:
            comment = "COMMENT='{}'".format(self._escape_comment(model._meta.table_description))
        return comment

    def _column_comment_generator(self, model, field, comments_array: List) -> str:
        comment = ""
        if field.description:
            comment = "COMMENT '{}'".format(self._escape_comment(field.description))
        return comment
