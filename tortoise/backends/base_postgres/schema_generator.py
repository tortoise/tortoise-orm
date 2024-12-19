from typing import TYPE_CHECKING, Any, List

from tortoise.backends.base.schema_generator import BaseSchemaGenerator
from tortoise.converters import encoders

if TYPE_CHECKING:  # pragma: nocoverage
    from .client import BasePostgresClient


class BasePostgresSchemaGenerator(BaseSchemaGenerator):
    DIALECT = "postgres"
    SCHEMA_CREATE_TEMPLATE = 'CREATE SCHEMA IF NOT EXISTS "{schema_name}";'
    TABLE_CREATE_TEMPLATE = 'CREATE TABLE {exists}{schema_name}"{table_name}" ({fields}){extra}{comment};'
    M2M_TABLE_TEMPLATE = (
        'CREATE TABLE {exists}{schema_name}"{table_name}" (\n'
        '    "{backward_key}" {backward_type} NOT NULL{backward_fk},\n'
        '    "{forward_key}" {forward_type} NOT NULL{forward_fk}\n'
        "){extra}{comment};"
    )
    TABLE_COMMENT_TEMPLATE = "COMMENT ON TABLE {schema_name}\"{table}\" IS '{comment}';"
    COLUMN_COMMENT_TEMPLATE = 'COMMENT ON COLUMN {schema_name}"{table}"."{column}" IS \'{comment}\';'
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

    def _column_comment_generator(self, schema_name, table: str, column: str, comment: str) -> str:
        comment = self.COLUMN_COMMENT_TEMPLATE.format(
            schema_name=schema_name,
            table=table,
            column=column,
            comment=self._escape_comment(comment)
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

    def _get_schema_name(self, model: "Type[Model]") -> str:
        schema_name = ""
        if model._meta.schema and model._meta.schema != 'public':
            schema_name = f'"{model._meta.schema}".'
        return schema_name

    def _get_schemas_to_create(self, models_to_create, schemas_to_create: "List[String]") -> None:
        for model in models_to_create:
            schema_name = ""
            if model._meta.schema and model._meta.schema != 'public':
                schema_name = model._meta.schema
            if schema_name and schema_name not in schemas_to_create:
                schemas_to_create.append(schema_name)