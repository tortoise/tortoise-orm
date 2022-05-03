from typing import TYPE_CHECKING, Any, List, Type

from tortoise.backends.base.schema_generator import BaseSchemaGenerator
from tortoise.converters import encoders
from tortoise.fields import CASCADE, SET_NULL

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.backends.oracle import OracleClient
    from tortoise.models import Model


class OracleSchemaGenerator(BaseSchemaGenerator):
    DIALECT = "oracle"
    TABLE_CREATE_TEMPLATE = 'CREATE TABLE "{table_name}" ({fields}){extra};'
    FIELD_TEMPLATE = '"{name}" {type}{default} {nullable} {unique}{primary}'
    TABLE_COMMENT_TEMPLATE = "COMMENT ON TABLE \"{table}\" IS '{comment}';"
    COLUMN_COMMENT_TEMPLATE = 'COMMENT ON COLUMN "{table}"."{column}" IS \'{comment}\';'
    INDEX_CREATE_TEMPLATE = 'CREATE INDEX "{index_name}" ON "{table_name}" ({fields});'
    GENERATED_PK_TEMPLATE = '"{field_name}" {generated_sql}'
    FK_TEMPLATE = (
        '{constraint}FOREIGN KEY ("{db_column}")'
        ' REFERENCES "{table}" ("{field}") ON DELETE {on_delete}'
    )
    M2M_TABLE_TEMPLATE = (
        'CREATE TABLE "{table_name}" (\n'
        '    "{backward_key}" {backward_type} NOT NULL,\n'
        '    "{forward_key}" {forward_type} NOT NULL,\n'
        "    {backward_fk},\n"
        "    {forward_fk}\n"
        "){extra};"
    )

    def __init__(self, client: "OracleClient") -> None:
        super().__init__(client)
        self._field_indexes: List[str] = []
        self._foreign_keys: List[str] = []
        self.comments_array: List[str] = []

    def quote(self, val: str) -> str:
        return f'"{val}"'

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
        if not (auto_now or auto_now_add):
            default_str += f" {default}"
        if auto_now_add:
            default_str += " CURRENT_TIMESTAMP"
        return default_str

    def _escape_default_value(self, default: Any):
        return encoders.get(type(default))(default)  # type: ignore

    def _get_index_sql(self, model: "Type[Model]", field_names: List[str], safe: bool) -> str:
        return super(OracleSchemaGenerator, self)._get_index_sql(model, field_names, False)

    def _get_table_sql(self, model: "Type[Model]", safe: bool = True) -> dict:
        return super(OracleSchemaGenerator, self)._get_table_sql(model, False)

    def _create_fk_string(
        self,
        constraint_name: str,
        db_column: str,
        table: str,
        field: str,
        on_delete: str,
        comment: str,
    ) -> str:
        if on_delete not in [CASCADE, SET_NULL]:
            on_delete = CASCADE
        constraint = f'CONSTRAINT "{constraint_name}" ' if constraint_name else ""
        fk = self.FK_TEMPLATE.format(
            constraint=constraint,
            db_column=db_column,
            table=table,
            field=field,
            on_delete=on_delete,
        )
        if constraint_name:
            self._foreign_keys.append(fk)
            return ""
        return fk
