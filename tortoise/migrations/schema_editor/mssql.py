from __future__ import annotations

from tortoise.fields.base import CASCADE
from tortoise.fields.relational import ManyToManyFieldInstance
from tortoise.migrations.schema_editor.base import BaseSchemaEditor
from tortoise.models import Model
from tortoise.schema_quoting import MSSQLQuotingMixin

# MSSQL sp_rename expects:
#   arg1: schema-qualified old name (e.g. '[schema].[old_name]')
#   arg2: unqualified new name only (e.g. 'new_name')
# This differs from standard ALTER TABLE RENAME where both sides are qualified.


class MSSQLSchemaEditor(MSSQLQuotingMixin, BaseSchemaEditor):
    DIALECT = "mssql"
    TABLE_CREATE_TEMPLATE = "CREATE TABLE {table_name} ({fields}){extra};"
    FIELD_TEMPLATE = "[{name}] {type} {nullable} {unique}{primary}"
    INDEX_CREATE_TEMPLATE = "CREATE INDEX [{index_name}] ON {table_name} ({fields});"
    GENERATED_PK_TEMPLATE = "[{field_name}] {generated_sql}"
    FK_TEMPLATE = (
        "{constraint}FOREIGN KEY ([{db_column}])"
        " REFERENCES {table} ([{field}]) ON DELETE {on_delete}"
    )
    M2M_TABLE_TEMPLATE = (
        "CREATE TABLE {table_name} (\n"
        "    {backward_key} {backward_type} NOT NULL,\n"
        "    {forward_key} {forward_type} NOT NULL,\n"
        "    {backward_fk},\n"
        "    {forward_fk}\n"
        "){extra};"
    )
    RENAME_TABLE_TEMPLATE = "EXEC sp_rename '{old_table}', '{new_table}'"
    DELETE_TABLE_TEMPLATE = "DROP TABLE {table}"
    ADD_FIELD_TEMPLATE = "ALTER TABLE {table} ADD {definition}"
    ALTER_FIELD_TEMPLATE = "ALTER TABLE {table} {changes}"
    RENAME_FIELD_TEMPLATE = "EXEC sp_rename '{table}.{old_column}', '{new_column}', 'COLUMN'"
    DELETE_FIELD_TEMPLATE = "ALTER TABLE {table} DROP COLUMN [{column}]"
    DROP_INDEX_TEMPLATE = "DROP INDEX [{name}] ON {table}"
    RENAME_INDEX_TEMPLATE = "EXEC sp_rename '{table}.{old_name}', '{new_name}', 'INDEX'"
    RENAME_CONSTRAINT_TEMPLATE = "EXEC sp_rename '{table}.{old_name}', '{new_name}', 'OBJECT'"

    def __init__(self, connection, atomic: bool = True, collect_sql: bool = False) -> None:
        super().__init__(connection, atomic, collect_sql=collect_sql)
        self._foreign_keys: list[str] = []

    async def create_schema(self, schema_name: str) -> None:
        await self._run_sql(
            f"IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = N'{schema_name}')"
            f" EXEC(N'CREATE SCHEMA [{schema_name}]');"
        )

    async def drop_schema(self, schema_name: str) -> None:
        await self._run_sql(f"DROP SCHEMA [{schema_name}];")

    async def rename_table(self, model: type[Model], old_name: str, new_name: str) -> None:
        if old_name == new_name:
            return
        schema = model._meta.schema
        await self._run_sql(
            self.RENAME_TABLE_TEMPLATE.format(
                old_table=self._qualify_table_name(old_name, schema),
                new_table=new_name,
            )
        )

    def _get_table_comment_sql(self, table: str, comment: str) -> str:
        return ""

    def _get_column_comment_sql(self, table: str, column: str, comment: str) -> str:
        return ""

    def _get_fk_reference_string(
        self,
        constraint_name: str,
        db_field: str,
        table: str,
        field: str,
        on_delete: str,
        comment: str,
    ) -> str:
        constraint = f"CONSTRAINT [{constraint_name}] " if constraint_name else ""
        fk = self.FK_TEMPLATE.format(
            constraint=constraint,
            db_column=db_field,
            table=table,
            field=field,
            on_delete=on_delete,
        )
        if constraint_name:
            self._foreign_keys.append(fk)
            return ""
        return fk

    def _get_inner_statements(self) -> list[str]:
        extra = list(dict.fromkeys(self._foreign_keys))
        self._foreign_keys.clear()
        return extra

    def _format_m2m_fk(self, table: str, column: str, target_table: str, target_field: str) -> str:
        return self.FK_TEMPLATE.format(
            constraint="",
            db_column=column,
            table=target_table,
            field=target_field,
            on_delete=CASCADE,
        )

    def _get_m2m_table_definition(
        self, model: type[Model], field: ManyToManyFieldInstance
    ) -> str | None:
        if field._generated:
            return None
        related_model = field.related_model
        if not related_model:
            return None
        m2m_schema = model._meta.schema
        backward_fk = self._format_m2m_fk(
            field.through,
            field.backward_key,
            self._qualify_table_name(model._meta.db_table, model._meta.schema),
            model._meta.db_pk_column,
        )
        forward_fk = self._format_m2m_fk(
            field.through,
            field.forward_key,
            self._qualify_table_name(related_model._meta.db_table, related_model._meta.schema),
            related_model._meta.db_pk_column,
        )
        m2m_create_string = self.M2M_TABLE_TEMPLATE.format(
            table_name=self._qualify_table_name(field.through, m2m_schema),
            backward_table=self._qualify_table_name(model._meta.db_table, model._meta.schema),
            forward_table=self._qualify_table_name(
                related_model._meta.db_table, related_model._meta.schema
            ),
            backward_field=model._meta.db_pk_column,
            forward_field=related_model._meta.db_pk_column,
            backward_key=field.backward_key,
            backward_type=model._meta.pk.get_for_dialect(self.DIALECT, "SQL_TYPE"),
            forward_key=field.forward_key,
            forward_type=related_model._meta.pk.get_for_dialect(self.DIALECT, "SQL_TYPE"),
            backward_fk=backward_fk,
            forward_fk=forward_fk,
            extra=self._table_generate_extra(table=field.through),
            comment="",
        )
        m2m_create_string += self._post_table_hook()
        if field.unique:
            unique_index_sql = self._get_unique_index_sql(
                field.through, [field.backward_key, field.forward_key]
            )
            if unique_index_sql.endswith(";"):
                m2m_create_string += "\n" + unique_index_sql
            else:
                lines = m2m_create_string.splitlines()
                if len(lines) > 1:
                    lines[-2] += ","
                    indent = "    "
                    lines.insert(-1, indent + unique_index_sql)
                    m2m_create_string = "\n".join(lines)
        return m2m_create_string

    async def remove_constraint(self, model, constraint) -> None:
        await self._run_sql(
            self.DELETE_CONSTRAINT_TEMPLATE.format(
                table=self._qualify_table_name(model._meta.db_table, model._meta.schema),
                name=self._constraint_name_for_model(model, constraint),
            )
        )

    async def remove_field(self, model: type[Model], field) -> None:
        if isinstance(field, ManyToManyFieldInstance):
            await self._run_sql(
                self.DELETE_TABLE_TEMPLATE.format(
                    table=self._qualify_table_name(field.through, model._meta.schema)
                )
            )
            return

        db_field = model._meta.fields_db_projection.get(
            field.model_field_name, field.source_field or field.model_field_name
        )
        qualified_table = self._qualify_table_name(model._meta.db_table, model._meta.schema)

        schema = model._meta.schema
        schema_filter = f" AND s.name = '{schema}'" if schema else ""
        cleanup_sql = f"""
DECLARE @sql NVARCHAR(MAX) = N'';
SELECT @sql += N'ALTER TABLE [' + s.name + '].[' + t.name + '] DROP CONSTRAINT [' + kc.name + '];'
FROM sys.key_constraints kc
JOIN sys.tables t ON kc.parent_object_id = t.object_id
JOIN sys.schemas s ON t.schema_id = s.schema_id
JOIN sys.index_columns ic ON kc.parent_object_id = ic.object_id AND kc.unique_index_id = ic.index_id
JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
WHERE t.name = '{model._meta.db_table}' AND c.name = '{db_field}'{schema_filter};
EXEC sp_executesql @sql;

SET @sql = N'';
SELECT @sql += N'DROP INDEX [' + i.name + '] ON [' + s.name + '].[' + t.name + '];'
FROM sys.indexes i
JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
JOIN sys.tables t ON i.object_id = t.object_id
JOIN sys.schemas s ON t.schema_id = s.schema_id
WHERE t.name = '{model._meta.db_table}' AND c.name = '{db_field}' AND i.is_unique = 1 AND i.is_primary_key = 0{schema_filter};
EXEC sp_executesql @sql;

SET @sql = N'';
SELECT @sql += N'ALTER TABLE [' + s.name + '].[' + t.name + '] DROP CONSTRAINT [' + dc.name + '];'
FROM sys.default_constraints dc
JOIN sys.columns c ON dc.parent_object_id = c.object_id AND dc.parent_column_id = c.column_id
JOIN sys.tables t ON dc.parent_object_id = t.object_id
JOIN sys.schemas s ON t.schema_id = s.schema_id
WHERE t.name = '{model._meta.db_table}' AND c.name = '{db_field}'{schema_filter};
EXEC sp_executesql @sql;
"""
        await self._run_sql(cleanup_sql)
        await self._run_sql(
            self.DELETE_FIELD_TEMPLATE.format(table=qualified_table, column=db_field)
        )
