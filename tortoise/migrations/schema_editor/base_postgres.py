from __future__ import annotations

from collections.abc import Sequence

from tortoise.migrations.schema_editor.base import BaseSchemaEditor
from tortoise.models import Model


class BasePostgresSchemaEditor(BaseSchemaEditor):
    DIALECT = "postgres"
    INDEX_CREATE_TEMPLATE = (
        'CREATE INDEX "{index_name}" ON "{table_name}" {index_type}({fields}){extra};'
    )
    UNIQUE_INDEX_CREATE_TEMPLATE = INDEX_CREATE_TEMPLATE.replace("INDEX", "UNIQUE INDEX")
    TABLE_COMMENT_TEMPLATE = "COMMENT ON TABLE \"{table}\" IS '{comment}';"
    COLUMN_COMMENT_TEMPLATE = 'COMMENT ON COLUMN "{table}"."{column}" IS \'{comment}\';'
    GENERATED_PK_TEMPLATE = '"{field_name}" {generated_sql}'

    def __init__(self, connection) -> None:
        super().__init__(connection)
        self.comments_array: list[str] = []

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

    def _get_unique_index_sql(self, table_name: str, field_names: list[str]) -> str:
        return self.UNIQUE_INDEX_CREATE_TEMPLATE.format(
            index_name=self._generate_index_name_for_table("uidx", table_name, field_names),
            table_name=table_name,
            index_type="",
            fields=", ".join([self.quote(f) for f in field_names]),
            extra="",
        )
