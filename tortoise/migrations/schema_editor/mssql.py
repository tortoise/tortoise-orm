from __future__ import annotations

from tortoise.fields.base import CASCADE
from tortoise.fields.relational import ManyToManyFieldInstance
from tortoise.migrations.schema_editor.base import BaseSchemaEditor
from tortoise.models import Model


class MSSQLSchemaEditor(BaseSchemaEditor):
    DIALECT = "mssql"
    TABLE_CREATE_TEMPLATE = "CREATE TABLE [{table_name}] ({fields}){extra};"
    FIELD_TEMPLATE = "[{name}] {type} {nullable} {unique}{primary}"
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
    RENAME_TABLE_TEMPLATE = "EXEC sp_rename '{old_table}', '{new_table}'"
    DELETE_TABLE_TEMPLATE = "DROP TABLE [{table}]"
    ADD_FIELD_TEMPLATE = "ALTER TABLE [{table}] ADD {definition}"
    ALTER_FIELD_TEMPLATE = "ALTER TABLE [{table}] {changes}"
    RENAME_FIELD_TEMPLATE = "EXEC sp_rename '{table}.{old_column}', '{new_column}', 'COLUMN'"
    DELETE_FIELD_TEMPLATE = "ALTER TABLE [{table}] DROP COLUMN [{column}]"
    DROP_INDEX_TEMPLATE = "DROP INDEX [{name}] ON [{table}]"
    RENAME_INDEX_TEMPLATE = "EXEC sp_rename '{table}.{old_name}', '{new_name}', 'INDEX'"
    RENAME_CONSTRAINT_TEMPLATE = "EXEC sp_rename '{table}.{old_name}', '{new_name}', 'OBJECT'"

    def __init__(self, connection, atomic: bool = True, collect_sql: bool = False) -> None:
        super().__init__(connection, atomic, collect_sql=collect_sql)
        self._foreign_keys: list[str] = []

    @staticmethod
    def quote(val: str) -> str:
        return f"[{val}]"

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
        backward_fk = self._format_m2m_fk(
            field.through,
            field.backward_key,
            model._meta.db_table,
            model._meta.db_pk_column,
        )
        forward_fk = self._format_m2m_fk(
            field.through,
            field.forward_key,
            related_model._meta.db_table,
            related_model._meta.db_pk_column,
        )
        m2m_create_string = self.M2M_TABLE_TEMPLATE.format(
            table_name=field.through,
            backward_table=model._meta.db_table,
            forward_table=related_model._meta.db_table,
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
                table=model._meta.db_table, name=self._constraint_name_for_model(model, constraint)
            )
        )

    async def remove_field(self, model: type[Model], field) -> None:
        if isinstance(field, ManyToManyFieldInstance):
            await self._run_sql(self.DELETE_TABLE_TEMPLATE.format(table=field.through))
            return

        db_field = model._meta.fields_db_projection.get(
            field.model_field_name, field.source_field or field.model_field_name
        )

        cleanup_sql = f"""
DECLARE @sql NVARCHAR(MAX) = N'';
SELECT @sql += N'ALTER TABLE [' + t.name + '] DROP CONSTRAINT [' + kc.name + '];'
FROM sys.key_constraints kc
JOIN sys.tables t ON kc.parent_object_id = t.object_id
JOIN sys.index_columns ic ON kc.parent_object_id = ic.object_id AND kc.unique_index_id = ic.index_id
JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
WHERE t.name = '{model._meta.db_table}' AND c.name = '{db_field}';
EXEC sp_executesql @sql;

SET @sql = N'';
SELECT @sql += N'DROP INDEX [' + i.name + '] ON [' + t.name + '];'
FROM sys.indexes i
JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
JOIN sys.tables t ON i.object_id = t.object_id
WHERE t.name = '{model._meta.db_table}' AND c.name = '{db_field}' AND i.is_unique = 1 AND i.is_primary_key = 0;
EXEC sp_executesql @sql;

SET @sql = N'';
SELECT @sql += N'ALTER TABLE [' + t.name + '] DROP CONSTRAINT [' + dc.name + '];'
FROM sys.default_constraints dc
JOIN sys.columns c ON dc.parent_object_id = c.object_id AND dc.parent_column_id = c.column_id
JOIN sys.tables t ON dc.parent_object_id = t.object_id
WHERE t.name = '{model._meta.db_table}' AND c.name = '{db_field}';
EXEC sp_executesql @sql;
"""
        await self._run_sql(cleanup_sql)
        await self._run_sql(
            self.DELETE_FIELD_TEMPLATE.format(table=model._meta.db_table, column=db_field)
        )
