from __future__ import annotations

from tortoise.fields import CASCADE, SET_NULL
from tortoise.fields.relational import ManyToManyFieldInstance
from tortoise.migrations.schema_editor.base import BaseSchemaEditor
from tortoise.models import Model


class OracleSchemaEditor(BaseSchemaEditor):
    DIALECT = "oracle"
    TABLE_CREATE_TEMPLATE = "CREATE TABLE {table_name} ({fields}){extra};"
    FIELD_TEMPLATE = '"{name}" {type} {nullable} {unique}{primary}'
    TABLE_COMMENT_TEMPLATE = "COMMENT ON TABLE {table} IS '{comment}';"
    COLUMN_COMMENT_TEMPLATE = "COMMENT ON COLUMN {table}.\"{column}\" IS '{comment}';"
    INDEX_CREATE_TEMPLATE = 'CREATE INDEX "{index_name}" ON {table_name} ({fields});'
    GENERATED_PK_TEMPLATE = '"{field_name}" {generated_sql}'
    FK_TEMPLATE = (
        '{constraint}FOREIGN KEY ("{db_column}")'
        ' REFERENCES {table} ("{field}") ON DELETE {on_delete}'
    )
    M2M_TABLE_TEMPLATE = (
        "CREATE TABLE {table_name} (\n"
        '    "{backward_key}" {backward_type} NOT NULL,\n'
        '    "{forward_key}" {forward_type} NOT NULL,\n'
        "    {backward_fk},\n"
        "    {forward_fk}\n"
        "){extra};"
    )
    DELETE_TABLE_TEMPLATE = "DROP TABLE {table} CASCADE CONSTRAINTS"
    DELETE_FIELD_TEMPLATE = 'ALTER TABLE {table} DROP COLUMN "{column}"'

    def __init__(self, connection, atomic: bool = True, collect_sql: bool = False) -> None:
        super().__init__(connection, atomic, collect_sql=collect_sql)
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

    def _get_fk_reference_string(
        self,
        constraint_name: str,
        db_field: str,
        table: str,
        field: str,
        on_delete: str,
        comment: str,
    ) -> str:
        if on_delete not in [CASCADE, SET_NULL]:
            on_delete = CASCADE
        _ = (constraint_name, db_field, table, field, on_delete, comment)
        return ""

    def _format_m2m_fk(self, table: str, column: str, target_table: str, target_field: str) -> str:
        return self.FK_TEMPLATE.format(
            constraint="",
            db_column=column,
            table=target_table,
            field=target_field,
            on_delete=CASCADE,
        )

    def _get_m2m_table_definition(
        self, model: type[Model], field: ManyToManyFieldInstance
    ) -> str | None:
        if field._generated:
            return None
        related_model = field.related_model
        if not related_model:
            return None
        m2m_schema = model._meta.schema
        backward_fk = self._format_m2m_fk(
            field.through,
            field.backward_key,
            self._qualify_table_name(model._meta.db_table, model._meta.schema),
            model._meta.db_pk_column,
        )
        forward_fk = self._format_m2m_fk(
            field.through,
            field.forward_key,
            self._qualify_table_name(related_model._meta.db_table, related_model._meta.schema),
            related_model._meta.db_pk_column,
        )
        m2m_create_string = self.M2M_TABLE_TEMPLATE.format(
            table_name=self._qualify_table_name(field.through, m2m_schema),
            backward_table=self._qualify_table_name(model._meta.db_table, model._meta.schema),
            forward_table=self._qualify_table_name(
                related_model._meta.db_table, related_model._meta.schema
            ),
            backward_field=model._meta.db_pk_column,
            forward_field=related_model._meta.db_pk_column,
            backward_key=field.backward_key,
            backward_type=model._meta.pk.get_for_dialect(self.DIALECT, "SQL_TYPE"),
            forward_key=field.forward_key,
            forward_type=related_model._meta.pk.get_for_dialect(self.DIALECT, "SQL_TYPE"),
            backward_fk=backward_fk,
            forward_fk=forward_fk,
            extra=self._table_generate_extra(table=field.through),
            comment="",
        )
        m2m_create_string += self._post_table_hook()
        if field.unique:
            unique_index_sql = self._get_unique_index_sql(
                field.through, [field.backward_key, field.forward_key], schema=m2m_schema
            )
            if unique_index_sql.endswith(";"):
                m2m_create_string += "\n" + unique_index_sql
            else:
                lines = m2m_create_string.splitlines()
                if len(lines) > 1:
                    lines[-2] += ","
                    indent = "    "
                    lines.insert(-1, indent + unique_index_sql)
                    m2m_create_string = "\n".join(lines)
        return m2m_create_string
