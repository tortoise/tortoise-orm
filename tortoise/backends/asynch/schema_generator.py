from typing import Any, List, Type, cast

from tortoise import ManyToManyFieldInstance, Model
from tortoise.backends.base.schema_generator import BaseSchemaGenerator
from tortoise.converters import encoders


class AsynchSchemaGenerator(BaseSchemaGenerator):
    DIALECT = "clickhouse"
    TABLE_CREATE_TEMPLATE = 'CREATE TABLE {exists} "{table_name}" ({fields}){extra};'
    FIELD_TEMPLATE = "{name} {type} {default}{comment}"
    M2M_TABLE_TEMPLATE = (
        'CREATE TABLE {exists}"{table_name}" (\n'
        '    "{backward_key}" {backward_type},'
        '    "{forward_key}" {forward_type}'
        "){extra}{comment};"
    )

    def _table_comment_generator(self, table: str, comment: str) -> str:
        return ""

    def _table_generate_extra(
        self, model: "Type[Model]", m2m_field: ManyToManyFieldInstance = None
    ) -> str:
        if m2m_field:
            return f"ENGINE = MergeTree ORDER BY ({m2m_field.backward_key},{m2m_field.forward_key})"  # type: ignore
        return f"ENGINE = MergeTree ORDER BY {model._meta.pk.source_field or model._meta.pk_attr}"  # type: ignore

    def _create_fk_string(
        self,
        constraint_name: str,
        db_column: str,
        table: str,
        field: str,
        on_delete: str,
        comment: str,
    ) -> str:
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
        if auto_now_add:
            default_str += " now()"
        else:
            default_str += f" {default}"
        return default_str

    def _escape_default_value(self, default: Any):
        return encoders.get(type(default))(default)  # type: ignore

    def _column_comment_generator(self, table: str, column: str, comment: str) -> str:
        return f" COMMENT '{self._escape_comment(comment)}'"

    def _get_unique_constraint_sql(self, model: "Type[Model]", field_names: List[str]) -> str:
        return ""

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
        if not nullable:
            field_type = f"Nullable({field_type})"
        return self.FIELD_TEMPLATE.format(
            name=db_column,
            type=field_type,
            comment=comment if self.client.capabilities.inline_comment else "",
            default=default,
        ).strip()

    def _get_index_sql(self, model: "Type[Model]", field_names: List[str], safe: bool) -> str:
        return ""
