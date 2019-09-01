from typing import Optional

from tortoise import fields
from tortoise.backends.base.schema_generator import BaseSchemaGenerator


class MySQLSchemaGenerator(BaseSchemaGenerator):
    TABLE_CREATE_TEMPLATE = "CREATE TABLE {exists}`{table_name}` ({fields}){extra}{comment};"
    INDEX_CREATE_TEMPLATE = "CREATE INDEX `{index_name}` ON `{table_name}` ({fields});"
    FIELD_TEMPLATE = "`{name}` {type} {nullable} {unique}{comment}"
    FK_TEMPLATE = "{comment} REFERENCES `{table}` (`{field}`) ON DELETE {on_delete}"
    M2M_TABLE_TEMPLATE = (
        "CREATE TABLE {exists}`{table_name}` (\n"
        "    `{backward_key}` {backward_type} NOT NULL REFERENCES `{backward_table}`"
        " (`{backward_field}`) ON DELETE CASCADE,\n"
        "    `{forward_key}` {forward_type} NOT NULL REFERENCES `{forward_table}`"
        " (`{forward_field}`) ON DELETE CASCADE\n"
        "){extra}{comment};"
    )
    FIELD_TYPE_MAP = {
        **BaseSchemaGenerator.FIELD_TYPE_MAP,
        fields.FloatField: "DOUBLE",
        fields.DatetimeField: "DATETIME(6)",
        fields.TextField: "TEXT",
    }

    def _get_primary_key_create_string(
        self, field_object: fields.Field, field_name: str, comment: str
    ) -> Optional[str]:
        if isinstance(field_object, fields.SmallIntField):
            return "`{}` SMALLINT UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT{}".format(
                field_name, comment
            )
        if isinstance(field_object, fields.IntField):
            return "`{}` INT UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT{}".format(
                field_name, comment
            )
        if isinstance(field_object, fields.BigIntField):
            return "`{}` BIGINT UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT{}".format(
                field_name, comment
            )
        return None

    def _table_generate_extra(self, table: str) -> str:
        return " CHARACTER SET {}".format(self.client.charset) if self.client.charset else ""

    def _table_comment_generator(self, table: str, comment: str) -> str:
        return " COMMENT='{}'".format(self._escape_comment(comment))

    def _column_comment_generator(self, table: str, column: str, comment: str) -> str:
        return " COMMENT '{}'".format(self._escape_comment(comment))
