from __future__ import annotations

from tortoise.indexes import Index
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

    async def add_constraint(self, model, constraint) -> None:
        await self.add_index(
            model,
            Index(fields=constraint.fields, name=constraint.name),
        )

    async def remove_constraint(self, model, constraint) -> None:
        await self.remove_index(
            model,
            Index(fields=constraint.fields, name=constraint.name),
        )

    async def rename_constraint(self, model, old_constraint, new_constraint) -> None:
        await self.rename_index(
            model,
            Index(fields=old_constraint.fields, name=old_constraint.name),
            Index(fields=new_constraint.fields, name=new_constraint.name),
        )
