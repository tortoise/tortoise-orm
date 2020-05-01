from typing import TYPE_CHECKING, List, Type

from tortoise.backends.base.schema_generator import BaseSchemaGenerator

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.backends.aioodbc.client import AioodbcDBClient
    from tortoise.models import Model


class AioodbcSchemaGenerator(BaseSchemaGenerator):
    DIALECT = "oracle"
    TABLE_CREATE_TEMPLATE = 'CREATE TABLE "{table_name}" ({fields});{extra}{comment}'
    FIELD_TEMPLATE = '"{name}" {type} {nullable} {unique}{primary}'
    INDEX_CREATE_TEMPLATE = 'CREATE INDEX "{index_name}" ON "{table_name}" ({fields});'
    UNIQUE_CONSTRAINT_CREATE_TEMPLATE = 'CONSTRAINT "{index_name}" UNIQUE ({fields})'
    GENERATED_PK_TEMPLATE = '"{field_name}" {generated_sql} PRIMARY KEY'
    PK_CONSTRAINT_TEMPLATE = 'CONSTRAINT "{table_name}_{field_name}" PRIMARY KEY ("{field_name}")'
    FK_TEMPLATE = (
        'CONSTRAINT "{constraint_name}" FOREIGN KEY ("{db_column}")'
        ' REFERENCES "{table}" ("{field}") ON DELETE {on_delete}'
    )
    M2M_TABLE_TEMPLATE = (
        'CREATE TABLE "{table_name}" (\n'
        '    "{backward_key}" {backward_type} NOT NULL,\n'
        '    "{forward_key}" {forward_type} NOT NULL,\n'
        '    FOREIGN KEY ("{backward_key}") REFERENCES "{backward_table}" ("{backward_field}")'
        " ON DELETE CASCADE,\n"
        '    FOREIGN KEY ("{forward_key}") REFERENCES "{forward_table}" ("{forward_field}")'
        " ON DELETE CASCADE\n"
        ");{extra}{comment}"
    )

    def __init__(self, client: "AioodbcDBClient") -> None:
        super().__init__(client)
        self._field_indexes = []  # type: List[str]
        self._foreign_keys = []  # type: List[str]

    def quote(self, val: str) -> str:
        return f'"{val}"'

    @classmethod
    def _get_escape_translation_table(cls) -> List[str]:
        """ Escape sequence taken based on
            https://docs.oracle.com/cd/B10501_01/text.920/a96518/cqspcl.htm """
        _escape_table = [chr(x) for x in range(128)]
        _escape_table[ord(",")] = "\\,"
        _escape_table[ord("&")] = "\\&"
        _escape_table[ord("?")] = "\\?"
        _escape_table[ord("{")] = "\\{"
        _escape_table[ord("}")] = "\\}"
        _escape_table[ord("\\")] = "\\\\"
        _escape_table[ord("(")] = "\\("
        _escape_table[ord(")")] = "\\)"
        _escape_table[ord("[")] = "\\["
        _escape_table[ord("]")] = "\\]"
        _escape_table[ord("-")] = "\\-"
        _escape_table[ord(";")] = "\\;"
        _escape_table[ord("~")] = "\\~"
        _escape_table[ord("|")] = "\\|"
        _escape_table[ord("$")] = "\\$"
        _escape_table[ord("!")] = "\\!"
        _escape_table[ord(">")] = "\\>"
        _escape_table[ord("*")] = "\\*"
        _escape_table[ord("%")] = "\\%"
        _escape_table[ord("_")] = "\\_"
        _escape_table[ord("'")] = "''"
        return _escape_table

    def _table_comment_generator(self, table: str, comment: str) -> str:
        return f"""\nCOMMENT ON TABLE "{table}" IS '{self._escape_comment(comment)}';"""

    def _column_comment_generator(self, table: str, column: str, comment: str) -> str:
        return f""" COMMENT ON COLUMN "{column}" IS '{self._escape_comment(comment)}';"""

    def _get_index_sql(self, model: "Type[Model]", field_names: List[str], safe: bool) -> str:
        """ Get index SQLs, but keep them for ourselves """
        self._field_indexes.append(
            self.INDEX_CREATE_TEMPLATE.format(
                index_name=self._generate_index_name("idx", model, field_names),
                table_name=model._meta.db_table,
                fields=", ".join([self.quote(f) for f in field_names]),
            )
        )
        return ""

    def _create_fk_string(
        self,
        constraint_name: str,
        db_column: str,
        table: str,
        field: str,
        on_delete: str,
        comment: str,
    ) -> str:
        self._foreign_keys.append(
            self.FK_TEMPLATE.format(
                constraint_name=constraint_name,
                db_column=db_column,
                table=table,
                field=field,
                on_delete=on_delete,
            )
        )
        return ""

    def _table_generate_extra(self, table: str) -> str:
        extra = list(dict.fromkeys(self._field_indexes))
        self._field_indexes.clear()
        return "\n".join(extra)

    def _get_inner_statements(self) -> List[str]:
        inner = self._foreign_keys
        self._foreign_keys.clear()
        return inner

    async def generate_from_string(self, creation_string: str) -> None:
        """ Override to create Schema one statement at a time. """
        queries = creation_string.split(";")
        queries = [query for query in queries if query]
        for query in queries:
            query = query + ";"
            await self.client.execute_script(query)
