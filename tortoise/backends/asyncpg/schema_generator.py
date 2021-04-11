from typing import TYPE_CHECKING, Any, List

from tortoise.backends.base.schema_generator import BaseSchemaGenerator
from tortoise.converters import encoders

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.backends.asyncpg.client import AsyncpgDBClient


class AsyncpgSchemaGenerator(BaseSchemaGenerator):
    DIALECT = "postgres"
    TABLE_COMMENT_TEMPLATE = "COMMENT ON TABLE \"{table}\" IS '{comment}';"
    COLUMN_COMMENT_TEMPLATE = 'COMMENT ON COLUMN "{table}"."{column}" IS \'{comment}\';'
    GENERATED_PK_TEMPLATE = '"{field_name}" {generated_sql}'

    def __init__(self, client: "AsyncpgDBClient") -> None:
        super().__init__(client)
        self.comments_array: List[str] = []

    @staticmethod
    def _table_generate_partition(partition_by: tuple) -> str:
         partition_string = ""
         if partition_by:
             partition_type, partition_by = partition_by[0].upper(), partition_by[1]
             partition_string = f" PARTITION BY {partition_type} ({partition_by})"
         return partition_string

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
        auto_now_add: bool = False,
        auto_now: bool = False,
    ) -> str:
        default_str = " DEFAULT"
        if auto_now_add:
            default_str += " CURRENT_TIMESTAMP"
        else:
            default_str += f" {default}"
        return default_str

    def _escape_default_value(self, default: Any):
        if isinstance(default, bool):
            return default
        return encoders.get(type(default))(default)  # type: ignore
