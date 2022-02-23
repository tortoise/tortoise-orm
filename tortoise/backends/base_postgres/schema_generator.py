from typing import TYPE_CHECKING, Any, List

from tortoise.backends.base.schema_generator import BaseSchemaGenerator
from tortoise.converters import encoders

if TYPE_CHECKING:  # pragma: nocoverage
    from .client import BasePostgresClient


class BasePostgresSchemaGenerator(BaseSchemaGenerator):
    DIALECT = "postgres"
    TABLE_COMMENT_TEMPLATE = "COMMENT ON TABLE \"{table}\" IS '{comment}';"
    COLUMN_COMMENT_TEMPLATE = 'COMMENT ON COLUMN "{table}"."{column}" IS \'{comment}\';'
    GENERATED_PK_TEMPLATE = '"{field_name}" {generated_sql}'

    def __init__(self, client: "BasePostgresClient") -> None:
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
        default_str += " CURRENT_TIMESTAMP" if auto_now_add else f" {default}"
        return default_str

    def _escape_default_value(self, default: Any):
        if isinstance(default, bool):
            return default
        return encoders.get(type(default))(default)  # type: ignore
