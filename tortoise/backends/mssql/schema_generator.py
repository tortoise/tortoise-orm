from typing import TYPE_CHECKING, Any, List, Type

from tortoise.backends.base.schema_generator import BaseSchemaGenerator
from tortoise.converters import encoders

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.backends.mssql import MSSQLClient
    from tortoise.models import Model


class MSSQLSchemaGenerator(BaseSchemaGenerator):
    DIALECT = "mssql"
    TABLE_CREATE_TEMPLATE = "CREATE TABLE [{table_name}] ({fields}){extra};"
    FIELD_TEMPLATE = "[{name}] {type} {nullable} {unique}{primary}{default}"
    INDEX_CREATE_TEMPLATE = "CREATE INDEX [{index_name}] ON [{table_name}] ({fields});"
    GENERATED_PK_TEMPLATE = "[{field_name}] {generated_sql}"
    FK_TEMPLATE = (
        "{constraint}FOREIGN KEY ([{db_column}])"
        " REFERENCES [{table}] ([{field}]) ON DELETE {on_delete}"
    )
    M2M_TABLE_TEMPLATE = (
        "CREATE TABLE [{table_name}] (\n"
        "    {backward_key} {backward_type} NOT NULL,\n"
        "    {forward_key} {forward_type} NOT NULL,\n"
        "    {backward_fk},\n"
        "    {forward_fk}\n"
        "){extra};"
    )

    def __init__(self, client: "MSSQLClient") -> None:
        super().__init__(client)
        self._field_indexes = []  # type: List[str]
        self._foreign_keys = []  # type: List[str]

    def quote(self, val: str) -> str:
        return f"[{val}]"

    def _table_comment_generator(self, table: str, comment: str) -> str:
        return ""

    def _column_comment_generator(self, table: str, column: str, comment: str) -> str:
        return ""

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
        if auto_now_add:
            default_str += " CURRENT_TIMESTAMP"
        return default_str

    def _escape_default_value(self, default: Any):
        return encoders.get(type(default))(default)  # type: ignore

    def _get_index_sql(self, model: "Type[Model]", field_names: List[str], safe: bool) -> str:
        return super(MSSQLSchemaGenerator, self)._get_index_sql(model, field_names, False)

    def _get_table_sql(self, model: "Type[Model]", safe: bool = True) -> dict:
        return super(MSSQLSchemaGenerator, self)._get_table_sql(model, False)

    def _create_fk_string(
        self,
        constraint_name: str,
        db_column: str,
        table: str,
        field: str,
        on_delete: str,
        comment: str,
    ) -> str:
        constraint = f"CONSTRAINT [{constraint_name}] " if constraint_name else ""
        fk = self.FK_TEMPLATE.format(
            constraint=constraint,
            db_column=db_column,
            table=table,
            field=field,
            on_delete=on_delete,
        )
        if constraint_name:
            self._foreign_keys.append(fk)
            return ""
        return fk

    def _create_string(
        self,
        db_column: str,
        field_type: str,
        nullable: str,
        unique: str,
        is_primary_key: bool,
        comment: str,
        default: str,
    ) -> str:
        if nullable == "":
            unique = ""
        return super(MSSQLSchemaGenerator, self)._create_string(
            db_column=db_column,
            field_type=field_type,
            nullable=nullable,
            unique=unique,
            is_primary_key=is_primary_key,
            comment=comment,
            default=default,
        )

    def _get_inner_statements(self) -> List[str]:
        extra = self._foreign_keys + list(dict.fromkeys(self._field_indexes))
        self._field_indexes.clear()
        self._foreign_keys.clear()
        return extra
