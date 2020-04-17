from typing import TYPE_CHECKING, List

from tortoise.backends.base.schema_generator import BaseSchemaGenerator

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.backends.asyncpg.client import AsyncpgDBClient


class AsyncpgSchemaGenerator(BaseSchemaGenerator):
    DIALECT = "postgres"
    TABLE_COMMENT_TEMPLATE = "COMMENT ON TABLE \"{table}\" IS '{comment}';"
    COLUMN_COMMNET_TEMPLATE = 'COMMENT ON COLUMN "{table}"."{column}" IS \'{comment}\';'
    GENERATED_PK_TEMPLATE = '"{field_name}" {generated_sql}'

    def __init__(self, client: "AsyncpgDBClient") -> None:
        super().__init__(client)
        self.comments_array: List[str] = []

    @classmethod
    def _get_escape_translation_table(cls) -> List[str]:
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
        comment = self.COLUMN_COMMNET_TEMPLATE.format(
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
