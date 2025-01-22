from __future__ import annotations

import re
from hashlib import sha256
from typing import TYPE_CHECKING, Any, Type, cast

from tortoise.exceptions import ConfigurationError
from tortoise.fields import JSONField, TextField, UUIDField
from tortoise.fields.relational import OneToOneFieldInstance
from tortoise.indexes import Index

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.backends.base.client import BaseDBAsyncClient
    from tortoise.fields import Field
    from tortoise.fields.relational import (
        ForeignKeyFieldInstance,
        ManyToManyFieldInstance,
    )
    from tortoise.models import Model

# pylint: disable=R0201


class BaseSchemaGenerator:
    DIALECT = "sql"
    TABLE_CREATE_TEMPLATE = 'CREATE TABLE {exists}"{table_name}" ({fields}){extra}{comment};'
    FIELD_TEMPLATE = '"{name}" {type}{nullable}{unique}{primary}{default}{comment}'
    INDEX_CREATE_TEMPLATE = (
        'CREATE {index_type}INDEX {exists}"{index_name}" ON "{table_name}" ({fields}){extra};'
    )
    UNIQUE_INDEX_CREATE_TEMPLATE = INDEX_CREATE_TEMPLATE.replace("INDEX", "UNIQUE INDEX")
    UNIQUE_CONSTRAINT_CREATE_TEMPLATE = 'CONSTRAINT "{index_name}" UNIQUE ({fields})'
    GENERATED_PK_TEMPLATE = '"{field_name}" {generated_sql}{comment}'
    FK_TEMPLATE = ' REFERENCES "{table}" ("{field}") ON DELETE {on_delete}{comment}'
    M2M_TABLE_TEMPLATE = (
        'CREATE TABLE {exists}"{table_name}" (\n'
        '    "{backward_key}" {backward_type} NOT NULL{backward_fk},\n'
        '    "{forward_key}" {forward_type} NOT NULL{forward_fk}\n'
        "){extra}{comment};"
    )

    def __init__(self, client: "BaseDBAsyncClient") -> None:
        self.client = client

    def _create_string(
        self,
        db_column: str,
        field_type: str,
        nullable: str,
        unique: str,
        is_primary_key: bool,
        comment: str,
        default: str,
    ) -> str:
        # children can override this function to customize their sql queries

        return self.FIELD_TEMPLATE.format(
            name=db_column,
            type=field_type,
            nullable=nullable,
            unique="" if is_primary_key else unique,
            comment=comment if self.client.capabilities.inline_comment else "",
            primary=" PRIMARY KEY" if is_primary_key else "",
            default=default,
        ).strip()

    def _create_fk_string(
        self,
        constraint_name: str,
        db_column: str,
        table: str,
        field: str,
        on_delete: str,
        comment: str,
    ) -> str:
        return self.FK_TEMPLATE.format(
            db_column=db_column, table=table, field=field, on_delete=on_delete, comment=comment
        )

    def _table_comment_generator(self, table: str, comment: str) -> str:
        # Databases have their own way of supporting comments for table level
        # needs to be implemented for each supported client
        raise NotImplementedError()  # pragma: nocoverage

    def _column_default_generator(
        self,
        table: str,
        column: str,
        default: Any,
        auto_now_add: bool = False,
        auto_now: bool = False,
    ) -> str:
        # Databases have their own way of supporting default for column level
        # needs to be implemented for each supported client
        raise NotImplementedError()  # pragma: nocoverage

    def _escape_default_value(self, default: Any):
        # Databases have their own way of supporting default value
        # needs to be implemented for each supported client
        raise NotImplementedError()

    def _column_comment_generator(self, table: str, column: str, comment: str) -> str:
        # Databases have their own way of supporting comments for column level
        # needs to be implemented for each supported client
        raise NotImplementedError()  # pragma: nocoverage

    def _post_table_hook(self) -> str:
        # This method provides a mechanism where you can perform a set of
        # operation on the database table after  it's initialized. This method
        # by default does nothing. If need be, it can be over-written
        return ""

    @classmethod
    def _get_escape_translation_table(cls) -> list[str]:
        """escape sequence taken based on definition provided by PostgreSQL and MySQL"""
        _escape_table = [chr(x) for x in range(128)]
        _escape_table[0] = "\\0"
        _escape_table[ord("\\")] = "\\\\"
        _escape_table[ord("\n")] = "\\n"
        _escape_table[ord("\r")] = "\\r"
        _escape_table[ord("\032")] = "\\Z"
        _escape_table[ord('"')] = '\\"'
        _escape_table[ord("'")] = "\\'"
        return _escape_table

    def _escape_comment(self, comment: str) -> str:
        # This method provides a default method to escape comment strings as per
        # default standard as applied under mysql like database. This can be
        # overwritten if required to match the database specific escaping.
        return comment.translate(self._get_escape_translation_table())

    def _table_generate_extra(self, table: str) -> str:
        return ""

    def _get_inner_statements(self) -> list[str]:
        return []

    def quote(self, val: str) -> str:
        return f'"{val}"'

    @staticmethod
    def _make_hash(*args: str, length: int) -> str:
        # Hash a set of string values and get a digest of the given length.
        return sha256(";".join(args).encode("utf-8")).hexdigest()[:length]

    def _generate_index_name(
        self, prefix: str, model: "Type[Model] | str", field_names: list[str]
    ) -> str:
        # NOTE: for compatibility, index name should not be longer than 30
        # characters (Oracle limit).
        # That's why we slice some of the strings here.
        table_name = model if isinstance(model, str) else model._meta.db_table
        index_name = "{}_{}_{}_{}".format(
            prefix,
            table_name[:11],
            field_names[0][:7],
            self._make_hash(table_name, *field_names, length=6),
        )
        return index_name

    def _generate_fk_name(
        self, from_table: str, from_field: str, to_table: str, to_field: str
    ) -> str:
        # NOTE: for compatibility, index name should not be longer than 30
        # characters (Oracle limit).
        # That's why we slice some of the strings here.
        index_name = "fk_{f}_{t}_{h}".format(
            f=from_table[:8],
            t=to_table[:8],
            h=self._make_hash(from_table, from_field, to_table, to_field, length=8),
        )
        return index_name

    def _get_index_sql(
        self,
        model: "Type[Model]",
        field_names: list[str],
        safe: bool,
        index_name: str | None = None,
        index_type: str | None = None,
        extra: str | None = None,
    ) -> str:
        return self.INDEX_CREATE_TEMPLATE.format(
            exists="IF NOT EXISTS " if safe else "",
            index_name=index_name or self._generate_index_name("idx", model, field_names),
            index_type=f"{index_type} " if index_type else "",
            table_name=model._meta.db_table,
            fields=", ".join([self.quote(f) for f in field_names]),
            extra=f"{extra}" if extra else "",
        )

    def _get_unique_index_sql(self, exists: str, table_name: str, field_names: list[str]) -> str:
        index_name = self._generate_index_name("uidx", table_name, field_names)
        return self.UNIQUE_INDEX_CREATE_TEMPLATE.format(
            exists=exists,
            index_name=index_name,
            index_type="",
            table_name=table_name,
            fields=", ".join([self.quote(f) for f in field_names]),
            extra="",
        )

    def _get_unique_constraint_sql(self, model: "Type[Model]", field_names: list[str]) -> str:
        return self.UNIQUE_CONSTRAINT_CREATE_TEMPLATE.format(
            index_name=self._generate_index_name("uid", model, field_names),
            fields=", ".join([self.quote(f) for f in field_names]),
        )

    def _get_pk_field_sql_type(self, pk_field: "Field") -> str:
        if isinstance(pk_field, OneToOneFieldInstance):
            return self._get_pk_field_sql_type(pk_field.related_model._meta.pk)
        if sql_type := pk_field.get_for_dialect(self.DIALECT, "SQL_TYPE"):
            return sql_type
        raise ConfigurationError(f"Can't get SQL type of {pk_field} for {self.DIALECT}")

    def _get_table_sql(self, model: "Type[Model]", safe: bool = True) -> dict:
        fields_to_create = []
        fields_with_index = []
        m2m_tables_for_create = []
        references = set()
        models_to_create: "list[Type[Model]]" = []

        self._get_models_to_create(models_to_create)
        models_tables = [model._meta.db_table for model in models_to_create]
        for field_name, column_name in model._meta.fields_db_projection.items():
            field_object = model._meta.fields_map[field_name]
            comment = (
                self._column_comment_generator(
                    table=model._meta.db_table, column=column_name, comment=field_object.description
                )
                if field_object.description
                else ""
            )

            default = field_object.default
            auto_now_add = getattr(field_object, "auto_now_add", False)
            auto_now = getattr(field_object, "auto_now", False)
            if default is not None or auto_now or auto_now_add:
                if callable(default) or isinstance(field_object, (UUIDField, TextField, JSONField)):
                    default = ""
                else:
                    default = field_object.to_db_value(default, model)
                    try:
                        default = self._column_default_generator(
                            model._meta.db_table,
                            column_name,
                            self._escape_default_value(default),
                            auto_now_add,
                            auto_now,
                        )
                    except NotImplementedError:
                        default = ""
            else:
                default = ""

            # TODO: PK generation needs to move out of schema generator.
            if field_object.pk:
                if field_object.generated:
                    generated_sql = field_object.get_for_dialect(self.DIALECT, "GENERATED_SQL")
                    if generated_sql:  # pragma: nobranch
                        fields_to_create.append(
                            self.GENERATED_PK_TEMPLATE.format(
                                field_name=column_name,
                                generated_sql=generated_sql,
                                comment=comment,
                            )
                        )
                        continue

            nullable = " NOT NULL" if not field_object.null else ""
            unique = " UNIQUE" if field_object.unique else ""

            if getattr(field_object, "reference", None):
                reference = cast("ForeignKeyFieldInstance", field_object.reference)
                comment = (
                    self._column_comment_generator(
                        table=model._meta.db_table,
                        column=column_name,
                        comment=reference.description,
                    )
                    if reference.description
                    else ""
                )

                to_field_name = reference.to_field_instance.source_field
                if not to_field_name:
                    to_field_name = reference.to_field_instance.model_field_name

                field_creation_string = self._create_string(
                    db_column=column_name,
                    field_type=field_object.get_for_dialect(self.DIALECT, "SQL_TYPE"),
                    nullable=nullable,
                    unique=unique,
                    is_primary_key=field_object.pk,
                    comment=comment if not reference.db_constraint else "",
                    default=default,
                ) + (
                    self._create_fk_string(
                        constraint_name=self._generate_fk_name(
                            model._meta.db_table,
                            column_name,
                            reference.related_model._meta.db_table,
                            to_field_name,
                        ),
                        db_column=column_name,
                        table=reference.related_model._meta.db_table,
                        field=to_field_name,
                        on_delete=reference.on_delete,
                        comment=comment,
                    )
                    if reference.db_constraint
                    else ""
                )
                references.add(reference.related_model._meta.db_table)
            else:
                field_creation_string = self._create_string(
                    db_column=column_name,
                    field_type=field_object.get_for_dialect(self.DIALECT, "SQL_TYPE"),
                    nullable=nullable,
                    unique=unique,
                    is_primary_key=field_object.pk,
                    comment=comment,
                    default=default,
                )

            fields_to_create.append(field_creation_string)

            if field_object.index and not field_object.pk:
                fields_with_index.append(column_name)

        if model._meta.unique_together:
            for unique_together_list in model._meta.unique_together:
                unique_together_to_create = []

                for field in unique_together_list:
                    field_object = model._meta.fields_map[field]
                    unique_together_to_create.append(field_object.source_field or field)

                fields_to_create.append(
                    self._get_unique_constraint_sql(model, unique_together_to_create)
                )

        _indexes = [
            self._get_index_sql(model, [field_name], safe=safe) for field_name in fields_with_index
        ]

        if model._meta.indexes:
            for index in model._meta.indexes:
                if isinstance(index, Index):
                    idx_sql = index.get_sql(self, model, safe)
                else:
                    fields = []
                    for field in index:
                        field_object = model._meta.fields_map[field]
                        fields.append(field_object.source_field or field)
                    idx_sql = self._get_index_sql(model, fields, safe=safe)

                if idx_sql:
                    _indexes.append(idx_sql)

        field_indexes_sqls = [val for val in list(dict.fromkeys(_indexes)) if val]

        fields_to_create.extend(self._get_inner_statements())

        table_fields_string = "\n    {}\n".format(",\n    ".join(fields_to_create))
        table_comment = (
            self._table_comment_generator(
                table=model._meta.db_table, comment=model._meta.table_description
            )
            if model._meta.table_description
            else ""
        )

        table_create_string = self.TABLE_CREATE_TEMPLATE.format(
            exists="IF NOT EXISTS " if safe else "",
            table_name=model._meta.db_table,
            fields=table_fields_string,
            comment=table_comment,
            extra=self._table_generate_extra(table=model._meta.db_table),
        )

        table_create_string = "\n".join([table_create_string, *field_indexes_sqls])

        table_create_string += self._post_table_hook()

        for m2m_field in model._meta.m2m_fields:
            field_object = cast("ManyToManyFieldInstance", model._meta.fields_map[m2m_field])
            if field_object._generated or field_object.through in models_tables:
                continue
            backward_key, forward_key = field_object.backward_key, field_object.forward_key
            backward_fk = forward_fk = ""
            if field_object.db_constraint:
                backward_fk = self._create_fk_string(
                    "",
                    backward_key,
                    model._meta.db_table,
                    model._meta.db_pk_column,
                    field_object.on_delete,
                    "",
                )
                forward_fk = self._create_fk_string(
                    "",
                    forward_key,
                    field_object.related_model._meta.db_table,
                    field_object.related_model._meta.db_pk_column,
                    field_object.on_delete,
                    "",
                )
            exists = "IF NOT EXISTS " if safe else ""
            table_name = field_object.through
            backward_type = self._get_pk_field_sql_type(model._meta.pk)
            forward_type = self._get_pk_field_sql_type(field_object.related_model._meta.pk)
            m2m_create_string = self.M2M_TABLE_TEMPLATE.format(
                exists=exists,
                table_name=table_name,
                backward_fk=backward_fk,
                forward_fk=forward_fk,
                backward_key=backward_key,
                backward_type=backward_type,
                forward_key=forward_key,
                forward_type=forward_type,
                extra=self._table_generate_extra(table=field_object.through),
                comment=(
                    self._table_comment_generator(
                        table=field_object.through, comment=field_object.description
                    )
                    if field_object.description
                    else ""
                ),
            )
            if not field_object.db_constraint:
                m2m_create_string = m2m_create_string.replace(
                    """,
    ,
    """,
                    "",
                )  # may have better way
            m2m_create_string += self._post_table_hook()
            if field_object.create_unique_index:
                unique_index_create_sql = self._get_unique_index_sql(
                    exists, table_name, [backward_key, forward_key]
                )
                if unique_index_create_sql.endswith(";"):
                    m2m_create_string += "\n" + unique_index_create_sql
                else:
                    lines = m2m_create_string.splitlines()
                    lines[-2] += ","
                    indent = m.group() if (m := re.match(r"\s+", lines[-2])) else ""
                    lines.insert(-1, indent + unique_index_create_sql)
                    m2m_create_string = "\n".join(lines)
            m2m_tables_for_create.append(m2m_create_string)

        return {
            "table": model._meta.db_table,
            "model": model,
            "table_creation_string": table_create_string,
            "references": references,
            "m2m_tables": m2m_tables_for_create,
        }

    def _get_models_to_create(self, models_to_create: "list[Type[Model]]") -> None:
        from tortoise import Tortoise

        for app in Tortoise.apps.values():
            for model in app.values():
                if model._meta.db == self.client:
                    model._check()
                    models_to_create.append(model)

    def get_create_schema_sql(self, safe: bool = True) -> str:
        models_to_create: "list[Type[Model]]" = []

        self._get_models_to_create(models_to_create)

        tables_to_create = []
        for model in models_to_create:
            tables_to_create.append(self._get_table_sql(model, safe))

        tables_to_create_count = len(tables_to_create)

        created_tables: set[dict] = set()
        ordered_tables_for_create: list[str] = []
        m2m_tables_to_create: list[str] = []
        while True:
            if len(created_tables) == tables_to_create_count:
                break
            try:
                next_table_for_create = next(
                    t
                    for t in tables_to_create
                    if t["references"].issubset(created_tables | {t["table"]})
                )
            except StopIteration:
                raise ConfigurationError("Can't create schema due to cyclic fk references")
            tables_to_create.remove(next_table_for_create)
            created_tables.add(next_table_for_create["table"])
            ordered_tables_for_create.append(next_table_for_create["table_creation_string"])
            m2m_tables_to_create += next_table_for_create["m2m_tables"]

        schema_creation_string = "\n".join(ordered_tables_for_create + m2m_tables_to_create)
        return schema_creation_string

    async def generate_from_string(self, creation_string: str) -> None:
        await self.client.execute_script(creation_string)
