from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from tortoise.backends.base.schema_generator import BaseSchemaGenerator
from tortoise.converters import encoders
from tortoise.models import Model

if TYPE_CHECKING:  # pragma: nocoverage
    from .client import BasePostgresClient


class BasePostgresSchemaGenerator(BaseSchemaGenerator):
    DIALECT = "postgres"
    INDEX_CREATE_TEMPLATE = (
        'CREATE INDEX {exists}"{index_name}" ON {table_name} {index_type}({fields}){extra};'
    )
    UNIQUE_INDEX_CREATE_TEMPLATE = INDEX_CREATE_TEMPLATE.replace("INDEX", "UNIQUE INDEX")
    TABLE_COMMENT_TEMPLATE = "COMMENT ON TABLE {table} IS '{comment}';"
    COLUMN_COMMENT_TEMPLATE = "COMMENT ON COLUMN {table}.\"{column}\" IS '{comment}';"
    GENERATED_PK_TEMPLATE = '"{field_name}" {generated_sql}'

    def __init__(self, client: BasePostgresClient) -> None:
        super().__init__(client)
        self.comments_array: list[str] = []

    def _get_schema_create_sql(self, schema: str, safe: bool) -> str:
        if safe:
            return f"CREATE SCHEMA IF NOT EXISTS {self.quote(schema)};"
        return f"CREATE SCHEMA {self.quote(schema)};"

    @classmethod
    def _get_escape_translation_table(cls) -> list[str]:
        table = super()._get_escape_translation_table()
        table[ord("'")] = "''"
        return table

    def _table_comment_generator(self, table: str, comment: str) -> str:
        comment = self.TABLE_COMMENT_TEMPLATE.format(
            table=table, comment=self._escape_comment(comment)
        )
        self.comments_array.append(comment)
        return ""

    def _column_comment_generator(self, table: str, column: str, comment: str) -> str:
        comment = self.COLUMN_COMMENT_TEMPLATE.format(
            table=table, column=column, comment=self._escape_comment(comment)
        )
        if comment not in self.comments_array:
            self.comments_array.append(comment)
        return ""

    def _post_table_hook(self) -> str:
        val = "\n".join(self.comments_array)
        self.comments_array = []
        if val:
            return "\n" + val
        return ""

    def _column_default_generator(
        self,
        table: str,
        column: str,
        default: Any,
    ) -> str:
        return f" DEFAULT {default}"

    def _escape_default_value(self, default: Any):
        if isinstance(default, bool):
            return default
        return encoders.get(type(default))(default)  # type: ignore

    def _get_index_sql(
        self,
        model: type[Model],
        field_names: Sequence[str],
        safe: bool,
        index_name: str | None = None,
        index_type: str | None = None,
        extra: str | None = None,
    ) -> str:
        if index_type:
            index_type = f"USING {index_type}"

        return super()._get_index_sql(
            model, field_names, safe, index_name=index_name, index_type=index_type, extra=extra
        )

    def _partial_unique_index_sqls(self, model: type[Model], safe: bool) -> list[str]:
        from tortoise.migrations.constraints import UniqueConstraint

        exists = "IF NOT EXISTS " if safe else ""
        sqls: list[str] = []
        for constraint in getattr(model._meta, "constraints", None) or ():
            if not isinstance(constraint, UniqueConstraint) or not constraint.condition:
                continue
            resolved_fields = self._resolve_fields_to_columns(model, constraint.fields)
            resolved = UniqueConstraint(
                fields=tuple(resolved_fields),
                name=constraint.name,
                condition=constraint.condition,
            )
            index_name = self._constraint_name_for_model(model, resolved)
            sqls.append(
                self.UNIQUE_INDEX_CREATE_TEMPLATE.format(
                    exists=exists,
                    index_name=index_name,
                    index_type="",
                    table_name=self._qualify_table_name(model._meta.db_table, model._meta.schema),
                    fields=", ".join(self.quote(field) for field in resolved_fields),
                    extra=f" WHERE {constraint.condition}",
                )
            )
        return sqls
