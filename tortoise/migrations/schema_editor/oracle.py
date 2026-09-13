from __future__ import annotations

from copy import copy

from tortoise.fields import CASCADE, SET_NULL
from tortoise.fields.base import Field
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
        self._foreign_keys: list[str] = []

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
        constraint_prefix = f'CONSTRAINT "{constraint_name}" ' if constraint_name else ""
        fk = self.FK_TEMPLATE.format(
            constraint=constraint_prefix,
            db_column=db_field,
            table=table,
            field=field,
            on_delete=on_delete,
        )
        if constraint_name:
            self._foreign_keys.append(fk)
            return ""
        return fk

    def _get_inner_statements(self) -> list[str]:
        extra = list(self._foreign_keys)
        self._foreign_keys.clear()
        return extra

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

    async def _alter_field(self, model: type[Model], old_field: Field, new_field: Field) -> None:
        """Override to use Oracle MODIFY syntax instead of ALTER COLUMN.

        Oracle does not support ``ALTER COLUMN``.  Nullability, type, and default
        changes must use ``ALTER TABLE ... MODIFY ("col" type ...)``.
        """
        db_field = new_field.source_field or new_field.model_field_name
        qualified_table = self._qualify_table_name(model._meta.db_table, model._meta.schema)

        # Handle nullability and type changes with MODIFY
        old_sql_type = old_field.get_for_dialect(self.DIALECT, "SQL_TYPE")
        new_sql_type = new_field.get_for_dialect(self.DIALECT, "SQL_TYPE")
        null_changed = old_field.null != new_field.null
        type_changed = old_sql_type != new_sql_type

        if null_changed or type_changed:
            nullable = "NULL" if new_field.null else "NOT NULL"
            await self._run_sql(
                f'ALTER TABLE {qualified_table} MODIFY ("{db_field}" {new_sql_type} {nullable})'
            )
            old_field = copy(old_field)
            old_field.null = new_field.null
            for attr in ("max_length", "max_digits", "decimal_places"):
                if hasattr(new_field, attr):
                    setattr(old_field, attr, getattr(new_field, attr))

        # Handle db_default changes with MODIFY
        old_has_default = old_field.has_db_default()
        new_has_default = new_field.has_db_default()
        if old_has_default != new_has_default or (
            old_has_default and new_has_default and old_field.db_default != new_field.db_default
        ):
            if new_has_default:
                if hasattr(new_field.db_default, "get_sql"):
                    default_sql = new_field.db_default.get_sql(dialect=self.DIALECT)
                else:
                    db_val = new_field.to_db_value(new_field.db_default, model)
                    default_sql = self._escape_default_value(db_val)
                await self._run_sql(
                    f'ALTER TABLE {qualified_table} MODIFY ("{db_field}" DEFAULT {default_sql})'
                )
            else:
                await self._run_sql(
                    f'ALTER TABLE {qualified_table} MODIFY ("{db_field}" DEFAULT NULL)'
                )
            old_field = copy(old_field)
            old_field.db_default = new_field.db_default

        # Let base handle index, unique, description, and rename
        await super()._alter_field(model, old_field, new_field)

    async def _get_unique_constraint_names_from_db(
        self, table_name: str, column_names: list[str], schema: str | None = None
    ) -> list[str]:
        """Query USER_CONSTRAINTS/ALL_CONSTRAINTS for unique constraint names matching exact columns."""
        upper_table = table_name.upper()
        col_count = len(column_names)
        col_list = ",".join(f"'{c.upper()}'" for c in column_names)
        if schema:
            query = (
                "SELECT ac.CONSTRAINT_NAME "
                "FROM ALL_CONSTRAINTS ac "
                "JOIN ALL_CONS_COLUMNS acc "
                "ON ac.CONSTRAINT_NAME = acc.CONSTRAINT_NAME "
                "AND ac.OWNER = acc.OWNER "
                f"WHERE ac.TABLE_NAME = '{upper_table}' "  # nosec B608
                f"AND acc.COLUMN_NAME IN ({col_list}) "
                "AND ac.CONSTRAINT_TYPE = 'U' "
                f"AND ac.OWNER = '{schema.upper()}' "
                "GROUP BY ac.CONSTRAINT_NAME "
                f"HAVING COUNT(DISTINCT acc.COLUMN_NAME) = {col_count} "
                "AND COUNT(DISTINCT acc.COLUMN_NAME) = ("
                "  SELECT COUNT(*) FROM ALL_CONS_COLUMNS acc2 "
                "  WHERE acc2.CONSTRAINT_NAME = ac.CONSTRAINT_NAME "
                "  AND acc2.OWNER = ac.OWNER"
                ")"
            )
        else:
            query = (
                "SELECT uc.CONSTRAINT_NAME "
                "FROM USER_CONSTRAINTS uc "
                "JOIN USER_CONS_COLUMNS ucc "
                "ON uc.CONSTRAINT_NAME = ucc.CONSTRAINT_NAME "
                f"WHERE uc.TABLE_NAME = '{upper_table}' "  # nosec B608
                f"AND ucc.COLUMN_NAME IN ({col_list}) "
                "AND uc.CONSTRAINT_TYPE = 'U' "
                "GROUP BY uc.CONSTRAINT_NAME "
                f"HAVING COUNT(DISTINCT ucc.COLUMN_NAME) = {col_count} "
                "AND COUNT(DISTINCT ucc.COLUMN_NAME) = ("
                "  SELECT COUNT(*) FROM USER_CONS_COLUMNS ucc2 "
                "  WHERE ucc2.CONSTRAINT_NAME = uc.CONSTRAINT_NAME"
                ")"
            )
        _, rows = await self.client.execute_query(query)
        return [row["CONSTRAINT_NAME"] for row in rows]
