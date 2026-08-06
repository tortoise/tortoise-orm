from __future__ import annotations

from collections.abc import Sequence

from tortoise.fields.base import Field
from tortoise.migrations.schema_editor.base import BaseSchemaEditor
from tortoise.models import Model


class BasePostgresSchemaEditor(BaseSchemaEditor):
    DIALECT = "postgres"
    INDEX_CREATE_TEMPLATE = (
        'CREATE INDEX "{index_name}" ON {table_name} {index_type}({fields}){extra};'
    )
    UNIQUE_INDEX_CREATE_TEMPLATE = INDEX_CREATE_TEMPLATE.replace("INDEX", "UNIQUE INDEX")
    TABLE_COMMENT_TEMPLATE = "COMMENT ON TABLE {table} IS '{comment}';"
    COLUMN_COMMENT_TEMPLATE = "COMMENT ON COLUMN {table}.\"{column}\" IS '{comment}';"
    GENERATED_PK_TEMPLATE = '"{field_name}" {generated_sql}'

    def __init__(self, connection, atomic: bool = True, collect_sql: bool = False) -> None:
        super().__init__(connection, atomic, collect_sql=collect_sql)
        self.comments_array: list[str] = []

    async def create_schema(self, schema_name: str) -> None:
        await self._run_sql(f"CREATE SCHEMA IF NOT EXISTS {self.quote(schema_name)};")

    async def drop_schema(self, schema_name: str) -> None:
        await self._run_sql(f"DROP SCHEMA IF EXISTS {self.quote(schema_name)} CASCADE;")

    @classmethod
    def _get_escape_translation_table(cls) -> list[str]:
        table = super()._get_escape_translation_table()
        table[ord("'")] = "''"
        return table

    def _get_table_comment_sql(self, table: str, comment: str) -> str:
        sql = self.TABLE_COMMENT_TEMPLATE.format(table=table, comment=self._escape_comment(comment))
        self.comments_array.append(sql)
        return ""

    def _get_column_comment_sql(self, table: str, column: str, comment: str) -> str:
        sql = self.COLUMN_COMMENT_TEMPLATE.format(
            table=table, column=column, comment=self._escape_comment(comment)
        )
        if sql not in self.comments_array:
            self.comments_array.append(sql)
        return ""

    def _post_table_hook(self) -> str:
        sql = "\n".join(self.comments_array)
        self.comments_array = []
        if sql:
            return "\n" + sql
        return ""

    async def _alter_column_comment(
        self, model: type[Model], old_field: Field, new_field: Field
    ) -> None:
        """Emit COMMENT ON COLUMN for PostgreSQL."""
        db_field = new_field.source_field or new_field.model_field_name
        qualified_table = self._qualify_table_name(model._meta.db_table, model._meta.schema)
        if new_field.description:
            comment = self._escape_comment(new_field.description)
            await self._run_sql(
                self.COLUMN_COMMENT_TEMPLATE.format(
                    table=qualified_table, column=db_field, comment=comment
                )
            )
        else:
            # Remove comment: SET NULL
            await self._run_sql(f'COMMENT ON COLUMN {qualified_table}."{db_field}" IS NULL;')

    def _get_index_sql(
        self,
        model: type[Model],
        field_names: Sequence[str],
        safe: bool = False,
        index_name: str | None = None,
        index_type: str | None = None,
        extra: str | None = None,
    ) -> str:
        if index_type:
            index_type = f"USING {index_type}"
        return super()._get_index_sql(
            model,
            list(field_names),
            safe,
            index_name=index_name,
            index_type=index_type,
            extra=extra,
        )

    def _escape_default_value(self, default: object) -> str:
        if isinstance(default, bool):
            return "TRUE" if default else "FALSE"
        return super()._escape_default_value(default)

    def _get_unique_index_sql(
        self, table_name: str, field_names: list[str], schema: str | None = None
    ) -> str:
        return self.UNIQUE_INDEX_CREATE_TEMPLATE.format(
            index_name=self._generate_index_name_for_table("uidx", table_name, field_names),
            table_name=self._qualify_table_name(table_name, schema),
            index_type="",
            fields=", ".join([self.quote(f) for f in field_names]),
            extra="",
        )

    async def add_constraint(self, model, constraint) -> None:
        from tortoise.migrations.constraints import UniqueConstraint

        if isinstance(constraint, UniqueConstraint) and constraint.condition:
            resolved_fields = self._resolve_fields_to_columns(model, constraint.fields)
            resolved_constraint = UniqueConstraint(
                fields=tuple(resolved_fields),
                name=constraint.name,
                condition=constraint.condition,
            )
            index_name = self._constraint_name_for_model(model, resolved_constraint)
            index_sql = (
                f'CREATE UNIQUE INDEX "{index_name}" '
                f"ON {self._qualify_table_name(model._meta.db_table, model._meta.schema)} "
                f"({', '.join([self.quote(f) for f in resolved_fields])}) "
                f"WHERE {constraint.condition}"
            )
            await self._run_sql(index_sql + ";")
            return
        await super().add_constraint(model, constraint)

    async def remove_constraint(self, model, constraint) -> None:
        from tortoise.migrations.constraints import UniqueConstraint

        if isinstance(constraint, UniqueConstraint) and constraint.condition:
            resolved_fields = self._resolve_fields_to_columns(model, constraint.fields)
            resolved_constraint = UniqueConstraint(
                fields=tuple(resolved_fields),
                name=constraint.name,
                condition=constraint.condition,
            )
            constraint_name = self._constraint_name_for_model(model, resolved_constraint)
            await self._run_sql(self.DROP_INDEX_TEMPLATE.format(name=constraint_name))
            return
        await super().remove_constraint(model, constraint)

    async def _get_unique_constraint_names_from_db(
        self, table_name: str, column_names: list[str], schema: str | None = None
    ) -> list[str]:
        """Query pg_constraint for unique constraint names matching exact column set."""
        nsp = schema or "public"
        col_array = "ARRAY[" + ",".join(f"'{c}'" for c in column_names) + "]"
        query = (
            "SELECT con.conname "
            "FROM pg_constraint con "
            "JOIN pg_class rel ON rel.oid = con.conrelid "
            "JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace "
            f"WHERE rel.relname = '{table_name}' "  # nosec B608
            "AND con.contype = 'u' "
            f"AND nsp.nspname = '{nsp}' "
            "AND ARRAY("
            "  SELECT att.attname::text"
            "  FROM unnest(con.conkey) WITH ORDINALITY AS k(attnum, ord)"
            "  JOIN pg_attribute att ON att.attrelid = con.conrelid AND att.attnum = k.attnum"
            "  ORDER BY k.ord"
            f") = {col_array}::text[]"
        )
        _, rows = await self.client.execute_query(query)
        return [row["conname"] for row in rows]
