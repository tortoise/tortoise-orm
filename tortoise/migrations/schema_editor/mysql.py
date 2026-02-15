from __future__ import annotations

from copy import copy

from tortoise.fields.base import CASCADE, Field
from tortoise.fields.relational import ManyToManyFieldInstance
from tortoise.migrations.schema_editor.base import BaseSchemaEditor
from tortoise.models import Model
from tortoise.schema_quoting import MySQLQuotingMixin


class MySQLSchemaEditor(MySQLQuotingMixin, BaseSchemaEditor):
    DIALECT = "mysql"
    TABLE_CREATE_TEMPLATE = "CREATE TABLE {table_name} ({fields}){extra}{comment};"
    FIELD_TEMPLATE = "`{name}` {type} {nullable} {unique}{primary}{comment}"
    INDEX_CREATE_TEMPLATE = "{index_type}KEY `{index_name}` ({fields}){extra}"
    UNIQUE_CONSTRAINT_CREATE_TEMPLATE = "UNIQUE KEY `{index_name}` ({fields})"
    GENERATED_PK_TEMPLATE = "`{field_name}` {generated_sql}{comment}"
    FK_TEMPLATE = (
        "{constraint}FOREIGN KEY (`{db_column}`)"
        " REFERENCES {table} (`{field}`) ON DELETE {on_delete}"
    )
    M2M_TABLE_TEMPLATE = (
        "CREATE TABLE {table_name} (\n"
        "    `{backward_key}` {backward_type} NOT NULL,\n"
        "    `{forward_key}` {forward_type} NOT NULL,\n"
        "    {backward_fk},\n"
        "    {forward_fk}\n"
        "){extra}{comment};"
    )
    RENAME_TABLE_TEMPLATE = "RENAME TABLE {old_table} TO {new_table}"
    DELETE_TABLE_TEMPLATE = "DROP TABLE {table}"
    ADD_FIELD_TEMPLATE = "ALTER TABLE {table} ADD COLUMN {definition}"
    ALTER_FIELD_TEMPLATE = "ALTER TABLE {table} {changes}"
    ALTER_FIELD_NULL_TEMPLATE = "ALTER COLUMN `{column}` DROP NOT NULL"
    ALTER_FIELD_NOT_NULL_TEMPLATE = "ALTER COLUMN `{column}` SET NOT NULL"
    ALTER_FIELD_SET_DEFAULT_TEMPLATE = "ALTER COLUMN `{column}` SET DEFAULT {default}"
    ALTER_FIELD_DROP_DEFAULT_TEMPLATE = "ALTER COLUMN `{column}` DROP DEFAULT"
    RENAME_FIELD_TEMPLATE = "ALTER TABLE {table} RENAME COLUMN `{old_column}` TO `{new_column}`"
    DELETE_FIELD_TEMPLATE = "ALTER TABLE {table} DROP COLUMN `{column}`"
    DROP_INDEX_TEMPLATE = "DROP INDEX `{name}` ON {table}"
    RENAME_INDEX_TEMPLATE = "ALTER TABLE {table} RENAME INDEX `{old_name}` TO `{new_name}`"
    RENAME_CONSTRAINT_TEMPLATE = RENAME_INDEX_TEMPLATE

    def __init__(self, connection, atomic: bool = True, collect_sql: bool = False) -> None:
        super().__init__(connection, atomic, collect_sql=collect_sql)
        self._field_indexes: list[str] = []
        self._foreign_keys: list[str] = []

    def _table_generate_extra(self, table: str) -> str:
        charset = getattr(self.client, "charset", None)
        return f" CHARACTER SET {charset}" if charset else ""

    def _get_table_comment_sql(self, table: str, comment: str) -> str:
        return f" COMMENT='{self._escape_comment(comment)}'"

    def _get_column_comment_sql(self, table: str, column: str, comment: str) -> str:
        return f" COMMENT '{self._escape_comment(comment)}'"

    def _get_fk_reference_string(
        self,
        constraint_name: str,
        db_field: str,
        table: str,
        field: str,
        on_delete: str,
        comment: str,
    ) -> str:
        constraint = f"CONSTRAINT `{constraint_name}` " if constraint_name else ""
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
        extra = self._foreign_keys + list(dict.fromkeys(self._field_indexes))
        self._field_indexes.clear()
        self._foreign_keys.clear()
        return extra

    def _get_index_sql(
        self,
        model: type[Model],
        field_names: list[str],
        safe: bool = False,
        index_name: str | None = None,
        index_type: str | None = None,
        extra: str | None = None,
    ) -> str:
        _ = safe
        index_sql = self.INDEX_CREATE_TEMPLATE.format(
            index_name=index_name or self._generate_index_name("idx", model, field_names),
            fields=", ".join([self.quote(f) for f in field_names]),
            index_type=f"{index_type} " if index_type else "",
            extra=f"{extra}" if extra else "",
        )
        self._field_indexes.append(index_sql)
        return ""

    def _format_m2m_fk(self, table: str, column: str, target_table: str, target_field: str) -> str:
        return self.FK_TEMPLATE.format(
            constraint="",
            db_column=column,
            table=target_table,
            field=target_field,
            on_delete=CASCADE,
        )

    def _get_unique_index_sql(
        self, table_name: str, field_names: list[str], schema: str | None = None
    ) -> str:
        return self.UNIQUE_CONSTRAINT_CREATE_TEMPLATE.format(
            index_name=self._generate_index_name_for_table("uidx", table_name, field_names),
            fields=", ".join([self.quote(f) for f in field_names]),
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
            comment=self._get_table_comment_sql(table=field.through, comment=field.description)
            if field.description
            else "",
        )
        m2m_create_string += self._post_table_hook()
        if field.unique:
            unique_index_sql = self._get_unique_index_sql(
                field.through, [field.backward_key, field.forward_key], schema=m2m_schema
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

    async def _alter_field(self, model: type[Model], old_field: Field, new_field: Field) -> None:
        # MySQL does not support ALTER COLUMN ... SET/DROP NOT NULL.
        # It requires MODIFY COLUMN with the full column type specification.
        if old_field.null != new_field.null:
            db_field = new_field.source_field or new_field.model_field_name
            qualified_table = self._qualify_table_name(model._meta.db_table, model._meta.schema)
            col_type = new_field.get_for_dialect(self.DIALECT, "SQL_TYPE")
            nullable = "NULL" if new_field.null else "NOT NULL"
            await self._run_sql(
                f"ALTER TABLE {qualified_table} MODIFY COLUMN"
                f" {self.quote(db_field)} {col_type} {nullable}"
            )
            # Patch old_field copy so base skips the null change
            old_field = copy(old_field)
            old_field.null = new_field.null

        await super()._alter_field(model, old_field, new_field)

    async def add_constraint(self, model, constraint) -> None:
        table = self._qualify_table_name(model._meta.db_table, model._meta.schema)
        index_name = self._generate_index_name_for_table(
            "uidx", model._meta.db_table, list(constraint.fields)
        )
        columns = ", ".join([self.quote(f) for f in constraint.fields])
        await self._run_sql(f"ALTER TABLE {table} ADD UNIQUE KEY `{index_name}` ({columns})")

    async def _get_unique_constraint_names_from_db(
        self, table_name: str, column_name: str, schema: str | None = None
    ) -> list[str]:
        """Query information_schema for unique constraint names on a specific column."""
        query = (
            "SELECT tc.CONSTRAINT_NAME "
            "FROM information_schema.table_constraints tc "
            "JOIN information_schema.key_column_usage kcu "
            "ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME "
            "AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA "
            "AND tc.TABLE_NAME = kcu.TABLE_NAME "
            f"WHERE tc.TABLE_NAME = '{table_name}' "  # nosec B608
            "AND tc.TABLE_SCHEMA = DATABASE() "
            "AND tc.CONSTRAINT_TYPE = 'UNIQUE' "
            f"AND kcu.COLUMN_NAME = '{column_name}' "
            "GROUP BY tc.CONSTRAINT_NAME "
            "HAVING COUNT(kcu.COLUMN_NAME) = 1"
        )
        _, rows = await self.client.execute_query(query)
        return [row["CONSTRAINT_NAME"] for row in rows]

    async def remove_constraint(self, model, constraint) -> None:
        constraint_name = await self._resolve_constraint_name(model, constraint)
        await self._run_sql(
            self.DROP_INDEX_TEMPLATE.format(
                table=self._qualify_table_name(model._meta.db_table, model._meta.schema),
                name=constraint_name,
            )
        )
