from typing import List, Optional

from tortoise import fields
from tortoise.backends.base.schema_generator import BaseSchemaGenerator


class MySQLSchemaGenerator(BaseSchemaGenerator):
    TABLE_CREATE_TEMPLATE = "CREATE TABLE {exists}`{table_name}` ({fields}){extra}{comment};"
    INDEX_CREATE_TEMPLATE = "KEY `{index_name}` ({fields})"
    FIELD_TEMPLATE = "`{name}` {type} {nullable} {unique}{primary}{comment}"
    FK_TEMPLATE = (
        "CONSTRAINT `{constraint_name}` FOREIGN KEY (`{db_field}`)"
        " REFERENCES `{table}` (`{field}`) ON DELETE {on_delete}"
    )
    M2M_TABLE_TEMPLATE = (
        "CREATE TABLE {exists}`{table_name}` (\n"
        "    `{backward_key}` {backward_type} NOT NULL,\n"
        "    `{forward_key}` {forward_type} NOT NULL,\n"
        "    FOREIGN KEY (`{backward_key}`) REFERENCES `{backward_table}` (`{backward_field}`)"
        " ON DELETE CASCADE,\n"
        "    FOREIGN KEY (`{forward_key}`) REFERENCES `{forward_table}` (`{forward_field}`)"
        " ON DELETE CASCADE\n"
        "){extra}{comment};"
    )
    FIELD_TYPE_MAP = {
        **BaseSchemaGenerator.FIELD_TYPE_MAP,
        fields.FloatField: "DOUBLE",
        fields.DatetimeField: "DATETIME(6)",
        fields.TextField: "TEXT",
    }

    def __init__(self, client) -> None:
        super().__init__(client)
        self._field_indexes = []  # type: List[str]
        self._foreign_keys = []  # type: List[str]

    def quote(self, val: str) -> str:
        return f"`{val}`"

    def _get_primary_key_create_string(
        self, field_object: fields.Field, field_name: str, comment: str
    ) -> Optional[str]:
        if isinstance(field_object, fields.SmallIntField):
            return f"`{field_name}` SMALLINT NOT NULL PRIMARY KEY AUTO_INCREMENT{comment}"
        if isinstance(field_object, fields.IntField):
            return f"`{field_name}` INT NOT NULL PRIMARY KEY AUTO_INCREMENT{comment}"
        if isinstance(field_object, fields.BigIntField):
            return f"`{field_name}` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT{comment}"
        return None

    def _table_generate_extra(self, table: str) -> str:
        return f" CHARACTER SET {self.client.charset}" if self.client.charset else ""

    def _table_comment_generator(self, table: str, comment: str) -> str:
        return f" COMMENT='{self._escape_comment(comment)}'"

    def _column_comment_generator(self, table: str, column: str, comment: str) -> str:
        return f" COMMENT '{self._escape_comment(comment)}'"

    def _get_index_sql(self, model, field_names: List[str], safe: bool) -> str:
        """ Get index SQLs, but keep them for ourselves """
        self._field_indexes.append(
            self.INDEX_CREATE_TEMPLATE.format(
                exists="IF NOT EXISTS " if safe else "",
                index_name=self._generate_index_name(model, field_names),
                table_name=model._meta.table,
                fields=", ".join([self.quote(f) for f in field_names]),
            )
        )
        return ""

    def _create_fk_string(
        self,
        constraint_name: str,
        db_field: str,
        table: str,
        field: str,
        on_delete: str,
        comment: str,
    ) -> str:
        self._foreign_keys.append(
            self.FK_TEMPLATE.format(
                constraint_name=constraint_name,
                db_field=db_field,
                table=table,
                field=field,
                on_delete=on_delete,
            )
        )
        return comment

    def _get_inner_statements(self) -> List[str]:
        extra = self._foreign_keys + self._field_indexes
        self._field_indexes.clear()
        self._foreign_keys.clear()
        return extra
