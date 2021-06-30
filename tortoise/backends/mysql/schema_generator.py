from typing import TYPE_CHECKING, Any, List, Type

from tortoise.backends.base.schema_generator import BaseSchemaGenerator
from tortoise.converters import encoders

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.backends.mysql.client import MySQLClient
    from tortoise.models import Model


class MySQLSchemaGenerator(BaseSchemaGenerator):
    DIALECT = "mysql"
    TABLE_CREATE_TEMPLATE = "CREATE TABLE {exists}`{table_name}` ({fields}){extra}{comment};"
    INDEX_CREATE_TEMPLATE = "KEY `{index_name}` ({fields})"
    UNIQUE_CONSTRAINT_CREATE_TEMPLATE = "UNIQUE KEY `{index_name}` ({fields})"
    FIELD_TEMPLATE = "`{name}` {type} {nullable} {unique}{primary}{comment}{default}"
    GENERATED_PK_TEMPLATE = "`{field_name}` {generated_sql}{comment}"
    FK_TEMPLATE = (
        "{constraint}FOREIGN KEY (`{db_column}`)"
        " REFERENCES `{table}` (`{field}`) ON DELETE {on_delete}"
    )
    M2M_TABLE_TEMPLATE = (
        "CREATE TABLE {exists}`{table_name}` (\n"
        "    `{backward_key}` {backward_type} NOT NULL,\n"
        "    `{forward_key}` {forward_type} NOT NULL,\n"
        "    {backward_fk},\n"
        "    {forward_fk}\n"
        "){extra}{comment};"
    )

    def __init__(self, client: "MySQLClient") -> None:
        super().__init__(client)
        self._field_indexes = []  # type: List[str]
        self._foreign_keys = []  # type: List[str]

    def quote(self, val: str) -> str:
        return f"`{val}`"

    def _table_generate_extra(self, table: str) -> str:
        return (
            f" CHARACTER SET {self.client.charset}" if self.client.charset else ""  # type: ignore
        )

    def _table_comment_generator(self, table: str, comment: str) -> str:
        return f" COMMENT='{self._escape_comment(comment)}'"

    def _column_comment_generator(self, table: str, column: str, comment: str) -> str:
        return f" COMMENT '{self._escape_comment(comment)}'"

    def _column_default_generator(
        self,
        table: str,
        column: str,
        default: Any,
        auto_now_add: bool = False,
        auto_now: bool = False,
    ) -> str:
        default_str = " DEFAULT"
        if not (auto_now or auto_now_add):
            default_str += f" {default}"
        else:
            if auto_now_add:
                default_str += " CURRENT_TIMESTAMP(6)"
            if auto_now:
                default_str += " ON UPDATE CURRENT_TIMESTAMP(6)"
        return default_str

    def _escape_default_value(self, default: Any):
        return encoders.get(type(default))(default)  # type: ignore

    def _get_index_sql(self, model: "Type[Model]", field_names: List[str], safe: bool) -> str:
        """Get index SQLs, but keep them for ourselves"""
        self._field_indexes.append(
            self.INDEX_CREATE_TEMPLATE.format(
                exists="IF NOT EXISTS " if safe else "",
                index_name=self._generate_index_name("idx", model, field_names),
                table_name=model._meta.db_table,
                fields=", ".join([self.quote(f) for f in field_names]),
            )
        )
        return ""

    def _create_fk_string(
        self,
        constraint_name: str,
        db_column: str,
        table: str,
        field: str,
        on_delete: str,
        comment: str,
    ) -> str:
        constraint = ""
        if constraint_name:
            constraint = f"CONSTRAINT `{constraint_name}` "
        fk = self.FK_TEMPLATE.format(
            constraint=constraint,
            db_column=db_column,
            table=table,
            field=field,
            on_delete=on_delete,
        )
        if constraint_name:
            self._foreign_keys.append(fk)
            return comment
        return fk

    def _get_inner_statements(self) -> List[str]:
        extra = self._foreign_keys + list(dict.fromkeys(self._field_indexes))
        self._field_indexes.clear()
        self._foreign_keys.clear()
        return extra
