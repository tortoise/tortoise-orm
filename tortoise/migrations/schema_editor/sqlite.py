from __future__ import annotations

from typing import cast

from tortoise.fields.relational import ForeignKeyFieldInstance, ManyToManyFieldInstance
from tortoise.indexes import Index
from tortoise.migrations.constraints import UniqueConstraint
from tortoise.migrations.schema_editor.base import BaseSchemaEditor


class SqliteSchemaEditor(BaseSchemaEditor):
    DIALECT = "sqlite"
    DELETE_TABLE_TEMPLATE = 'DROP TABLE "{table}"'
    DELETE_FIELD_TEMPLATE = 'ALTER TABLE "{table}" DROP COLUMN "{column}"'
    DROP_INDEX_TEMPLATE = 'DROP INDEX "{name}"'
    RENAME_INDEX_TEMPLATE = None

    @classmethod
    def _get_escape_translation_table(cls) -> list[str]:
        table = super()._get_escape_translation_table()
        table[ord('"')] = '"'
        table[ord("'")] = "'"
        table[ord("/")] = "\\/"
        return table

    def _get_table_comment_sql(self, table: str, comment: str) -> str:
        return f" /* {self._escape_comment(comment)} */"

    def _get_column_comment_sql(self, table: str, column: str, comment: str) -> str:
        return f" /* {self._escape_comment(comment)} */"

    async def add_field(self, model, field_name: str) -> None:
        field = model._meta.fields_map[field_name]
        if isinstance(field, ManyToManyFieldInstance):
            table_string = self._get_m2m_table_definition(model, field)
            if table_string:
                await self.client.execute_script(table_string)
            return
        if isinstance(field, ForeignKeyFieldInstance):
            key_field_name = field.source_field or field_name
            db_field = model._meta.fields_db_projection.get(key_field_name, key_field_name)
            key_field = model._meta.fields_map[key_field_name]
            fk_field = cast(ForeignKeyFieldInstance, key_field.reference)
            comment = (
                self._get_column_comment_sql(
                    table=model._meta.db_table,
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
                table=fk_field.related_model._meta.db_table,
                field=to_field_name,
                on_delete=fk_field.on_delete,
                comment=comment,
            )
            unique_field = key_field.unique and not key_field.pk
        else:
            db_field = model._meta.fields_db_projection[field_name]
            comment = (
                self._get_column_comment_sql(
                    table=model._meta.db_table, column=db_field, comment=field.description
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

        await self.client.execute_script(
            self.ADD_FIELD_TEMPLATE.format(table=model._meta.db_table, definition=field_definition)
        )

        if unique_field:
            await self.add_constraint(model, UniqueConstraint(fields=(db_field,)))

    async def add_constraint(self, model, constraint) -> None:
        constraint_name = self._constraint_name_for_model(model, constraint)
        index_sql = self.UNIQUE_INDEX_CREATE_TEMPLATE.format(
            index_name=constraint_name,
            table_name=model._meta.db_table,
            fields=", ".join([self.quote(f) for f in constraint.fields]),
            extra="",
        )
        await self.client.execute_script(index_sql)

    async def remove_constraint(self, model, constraint) -> None:
        constraint_name = self._constraint_name_for_model(model, constraint)
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
