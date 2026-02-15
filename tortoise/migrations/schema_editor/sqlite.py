from __future__ import annotations

from typing import cast

from tortoise.fields.base import DB_DEFAULT_NOT_SET
from tortoise.fields.relational import (
    BackwardFKRelation,
    BackwardOneToOneRelation,
    ForeignKeyFieldInstance,
    ManyToManyFieldInstance,
)
from tortoise.indexes import Index
from tortoise.migrations.constraints import UniqueConstraint
from tortoise.migrations.schema_editor.base import BaseSchemaEditor
from tortoise.schema_quoting import SqliteQuotingMixin


class SqliteSchemaEditor(SqliteQuotingMixin, BaseSchemaEditor):
    DIALECT = "sqlite"
    DELETE_TABLE_TEMPLATE = "DROP TABLE {table}"
    DELETE_FIELD_TEMPLATE = 'ALTER TABLE {table} DROP COLUMN "{column}"'
    DROP_INDEX_TEMPLATE = 'DROP INDEX "{name}"'
    RENAME_INDEX_TEMPLATE = None

    @classmethod
    def _get_escape_translation_table(cls) -> list[str]:
        table = super()._get_escape_translation_table()
        table[ord('"')] = '"'
        table[ord("'")] = "'"
        table[ord("/")] = "\\/"
        return table

    async def _run_sql(self, sql: str) -> None:
        """Execute DDL SQL on SQLite.

        In atomic mode, uses execute_query() per statement because
        sqlite3.executescript() issues an implicit COMMIT.

        In collect_sql mode, delegates to the base class to collect
        the SQL without splitting or executing.
        """
        if self.collect_sql:
            await super()._run_sql(sql)
            return
        if self.atomic_migration:
            for statement in sql.split(";"):
                statement = statement.strip()
                if statement:
                    await self.client.execute_query(statement)
        else:
            await self.client.execute_script(sql)

    def _get_table_comment_sql(self, table: str, comment: str) -> str:
        return f" /* {self._escape_comment(comment)} */"

    def _get_column_comment_sql(self, table: str, column: str, comment: str) -> str:
        return f" /* {self._escape_comment(comment)} */"

    async def add_field(self, model, field_name: str) -> None:
        field = model._meta.fields_map[field_name]
        if isinstance(field, ManyToManyFieldInstance):
            table_string = self._get_m2m_table_definition(model, field)
            if table_string:
                await self._run_sql(table_string)
            return
        qualified_table = self._qualify_table_name(model._meta.db_table, model._meta.schema)
        if isinstance(field, ForeignKeyFieldInstance):
            key_field_name = field.source_field or field_name
            db_field = model._meta.fields_db_projection.get(key_field_name, key_field_name)
            key_field = model._meta.fields_map[key_field_name]
            fk_field = cast(ForeignKeyFieldInstance, key_field.reference)
            comment = (
                self._get_column_comment_sql(
                    table=qualified_table,
                    column=db_field,
                    comment=fk_field.description,
                )
                if fk_field.description
                else ""
            )

            to_field_name = fk_field.to_field_instance.source_field
            if not to_field_name:
                to_field_name = fk_field.to_field_instance.model_field_name

            field_definition = self._get_field_sql(
                db_field=db_field,
                field_type=key_field.get_for_dialect(self.DIALECT, "SQL_TYPE"),
                nullable=key_field.null,
                unique=False,
                is_pk=key_field.pk,
                comment="",
            ) + self._get_fk_reference_string(
                constraint_name=self._generate_fk_name(
                    model._meta.db_table,
                    db_field,
                    fk_field.related_model._meta.db_table,
                    to_field_name,
                ),
                db_field=db_field,
                table=self._qualify_table_name(
                    fk_field.related_model._meta.db_table, fk_field.related_model._meta.schema
                ),
                field=to_field_name,
                on_delete=fk_field.on_delete,
                comment=comment,
            )
            unique_field = key_field.unique and not key_field.pk
        else:
            db_field = model._meta.fields_db_projection[field_name]
            comment = (
                self._get_column_comment_sql(
                    table=qualified_table, column=db_field, comment=field.description
                )
                if field.description
                else ""
            )

            field_definition = self._get_field_sql(
                db_field=db_field,
                field_type=field.get_for_dialect(self.DIALECT, "SQL_TYPE"),
                nullable=field.null,
                unique=False,
                is_pk=field.pk,
                comment=comment,
            )
            unique_field = field.unique and not field.pk

        if field.has_db_default():
            if hasattr(field.db_default, "get_sql"):
                field_definition += f" DEFAULT {field.db_default.get_sql(dialect=self.DIALECT)}"
            else:
                db_val = field.to_db_value(field.db_default, model)
                escaped = self._escape_default_value(db_val)
                field_definition += f" DEFAULT {escaped}"

        await self._run_sql(
            self.ADD_FIELD_TEMPLATE.format(table=qualified_table, definition=field_definition)
        )

        if unique_field:
            await self.add_constraint(model, UniqueConstraint(fields=(db_field,)))

    async def add_constraint(self, model, constraint) -> None:
        constraint_name = self._constraint_name_for_model(model, constraint)
        index_sql = self.UNIQUE_INDEX_CREATE_TEMPLATE.format(
            index_name=constraint_name,
            table_name=self._qualify_table_name(model._meta.db_table, model._meta.schema),
            fields=", ".join([self.quote(f) for f in constraint.fields]),
            extra="",
        )
        await self._run_sql(index_sql)

    async def _get_unique_constraint_names_from_db(
        self, table_name: str, column_name: str, schema: str | None = None
    ) -> list[str]:
        """Use PRAGMA index_list + PRAGMA index_info to find unique index names."""
        _, indexes = await self.client.execute_query(f'PRAGMA index_list("{table_name}")')
        result: list[str] = []
        for idx in indexes:
            if not idx.get("unique"):
                continue
            idx_name = idx.get("name", "")
            _, columns = await self.client.execute_query(f'PRAGMA index_info("{idx_name}")')
            col_names = [col.get("name") for col in columns]
            if col_names == [column_name]:
                result.append(idx_name)
        return result

    async def remove_constraint(self, model, constraint) -> None:
        constraint_name = await self._resolve_constraint_name(model, constraint)
        await self.remove_index(
            model,
            Index(fields=constraint.fields, name=constraint_name),
        )

    async def rename_constraint(self, model, old_constraint, new_constraint) -> None:
        old_name = self._constraint_name_for_model(model, old_constraint)
        new_name = self._constraint_name_for_model(model, new_constraint)
        await self.rename_index(
            model,
            Index(fields=old_constraint.fields, name=old_name),
            Index(fields=new_constraint.fields, name=new_name),
        )

    async def remove_field(self, model, field) -> None:
        if isinstance(field, ManyToManyFieldInstance):
            await self._run_sql(
                self.DELETE_TABLE_TEMPLATE.format(
                    table=self._qualify_table_name(field.through, model._meta.schema)
                )
            )
            return
        await self._remake_table(model, delete_field=field)

    async def _alter_field(self, model, old_field, new_field) -> None:
        old_db_field = old_field.source_field or old_field.model_field_name
        new_db_field = new_field.source_field or new_field.model_field_name

        # Simple rename with no other changes can use RENAME COLUMN
        if (
            old_db_field != new_db_field
            and old_field.null == new_field.null
            and old_field.unique == new_field.unique
            and old_field.index == new_field.index
            and getattr(old_field, "db_default", DB_DEFAULT_NOT_SET)
            == getattr(new_field, "db_default", DB_DEFAULT_NOT_SET)
            and not old_field.pk
            and not new_field.pk
        ):
            qualified_table = self._qualify_table_name(model._meta.db_table, model._meta.schema)
            rename_sql = (
                f'ALTER TABLE {qualified_table} RENAME COLUMN "{old_db_field}" TO "{new_db_field}"'
            )
            await self._run_sql(rename_sql)
            return

        await self._remake_table(model, alter_fields=[(old_field, new_field)])

    async def _remake_table(
        self,
        model,
        create_field=None,
        delete_field=None,
        alter_fields=None,
    ) -> None:
        """Recreate a table with modified schema (SQLite's recommended ALTER TABLE approach)."""
        alter_fields = alter_fields or []
        db_table = model._meta.db_table
        new_table_name = f"new__{db_table}"

        column_mapping = {}
        for field in model._meta.fields_map.values():
            if isinstance(
                field, (ManyToManyFieldInstance, BackwardFKRelation, BackwardOneToOneRelation)
            ):
                continue
            db_field = field.source_field or field.model_field_name
            column_mapping[db_field] = self.quote(db_field)

        if create_field:
            if not isinstance(
                create_field,
                (ManyToManyFieldInstance, BackwardFKRelation, BackwardOneToOneRelation),
            ):
                db_field = create_field.source_field or create_field.model_field_name
                if create_field.default is not None:
                    default_value = create_field.default
                    default_val = self._default_to_sql_literal(default_value)
                    column_mapping[db_field] = default_val
                else:
                    column_mapping[db_field] = "NULL"

        for old_field, new_field in alter_fields:
            old_db_field = old_field.source_field or old_field.model_field_name
            new_db_field = new_field.source_field or new_field.model_field_name
            column_mapping.pop(old_db_field, None)

            if old_field.null and not new_field.null and new_field.default is not None:
                default_val = self._default_to_sql_literal(new_field.default)
                column_mapping[new_db_field] = (
                    f"COALESCE({self.quote(old_db_field)}, {default_val})"
                )
            else:
                column_mapping[new_db_field] = self.quote(old_db_field)

        if delete_field:
            if not isinstance(delete_field, ManyToManyFieldInstance):
                db_field = delete_field.source_field or delete_field.model_field_name
                column_mapping.pop(db_field, None)

        fields_by_db_column = {}
        for field in model._meta.fields_map.values():
            if isinstance(
                field, (ManyToManyFieldInstance, BackwardFKRelation, BackwardOneToOneRelation)
            ):
                continue
            if not hasattr(field, "get_for_dialect"):
                continue
            if delete_field and field.model_field_name == delete_field.model_field_name:
                continue

            actual_field = field
            for old_f, new_f in alter_fields:
                if field.model_field_name == old_f.model_field_name:
                    actual_field = new_f
                    break

            if create_field and field.model_field_name == create_field.model_field_name:
                actual_field = create_field

            db_field = actual_field.source_field or actual_field.model_field_name
            if db_field in fields_by_db_column:
                continue
            fields_by_db_column[db_field] = actual_field

        field_definitions = []
        for db_field, actual_field in fields_by_db_column.items():
            if isinstance(actual_field, ForeignKeyFieldInstance):
                fk_field = actual_field
                to_field_name = (
                    fk_field.to_field_instance.source_field
                    or fk_field.to_field_instance.model_field_name
                )
                field_type = fk_field.to_field_instance.get_for_dialect(self.DIALECT, "SQL_TYPE")

                field_def = self._get_field_sql(
                    db_field=db_field,
                    field_type=field_type,
                    nullable=actual_field.null,
                    unique=False,
                    is_pk=actual_field.pk,
                    comment="",
                ) + self._get_fk_reference_string(
                    constraint_name=self._generate_fk_name(
                        db_table,
                        db_field,
                        fk_field.related_model._meta.db_table,
                        to_field_name,
                    ),
                    db_field=db_field,
                    table=self._qualify_table_name(
                        fk_field.related_model._meta.db_table,
                        fk_field.related_model._meta.schema,
                    ),
                    field=to_field_name,
                    on_delete=fk_field.on_delete,
                    comment="",
                )
            else:
                field_def = self._get_field_sql(
                    db_field=db_field,
                    field_type=actual_field.get_for_dialect(self.DIALECT, "SQL_TYPE"),
                    nullable=actual_field.null,
                    unique=actual_field.unique and not actual_field.pk,
                    is_pk=actual_field.pk,
                    comment="",
                )

            if actual_field.has_db_default():
                if hasattr(actual_field.db_default, "get_sql"):
                    field_def += f" DEFAULT {actual_field.db_default.get_sql(dialect=self.DIALECT)}"
                else:
                    db_val = actual_field.to_db_value(actual_field.db_default, model)
                    escaped = self._escape_default_value(db_val)
                    field_def += f" DEFAULT {escaped}"

            field_definitions.append(field_def)

        qualified_new = self._qualify_table_name(new_table_name, model._meta.schema)
        qualified_old = self._qualify_table_name(db_table, model._meta.schema)
        create_sql = f"CREATE TABLE {qualified_new} ({', '.join(field_definitions)})"
        await self._run_sql(create_sql)

        if column_mapping:
            columns = list(column_mapping.keys())
            values = list(column_mapping.values())
            insert_sql = f"""INSERT INTO {qualified_new} ({", ".join(self.quote(c) for c in columns)})
                SELECT {", ".join(values)}
                FROM {qualified_old}"""  # nosec B608
            await self._run_sql(insert_sql)

        await self._run_sql(f"DROP TABLE {qualified_old}")
        await self._run_sql(f"ALTER TABLE {qualified_new} RENAME TO {qualified_old}")

    @staticmethod
    def _default_to_sql_literal(value) -> str:
        from decimal import Decimal

        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, str):
            return f"'{value}'"
        if isinstance(value, bool):
            return "1" if value else "0"
        return str(value)
