from __future__ import annotations

from hashlib import sha256
from typing import cast

from tortoise.backends.base.client import BaseDBAsyncClient
from tortoise.fields.base import Field
from tortoise.fields.relational import ForeignKeyFieldInstance, ManyToManyFieldInstance
from tortoise.indexes import Index
from tortoise.migrations.constraints import UniqueConstraint
from tortoise.migrations.schema_editor.data import ModelSqlData
from tortoise.models import Model


class BaseSchemaEditor:
    DIALECT = "sql"
    TABLE_CREATE_TEMPLATE = 'CREATE TABLE "{table_name}" ({fields}){extra}{comment};'
    FIELD_TEMPLATE = '"{name}" {type} {nullable} {unique}{primary}{comment}'
    INDEX_CREATE_TEMPLATE = 'CREATE INDEX "{index_name}" ON "{table_name}" ({fields}){extra};'
    UNIQUE_INDEX_CREATE_TEMPLATE = INDEX_CREATE_TEMPLATE.replace("INDEX", "UNIQUE INDEX")
    UNIQUE_CONSTRAINT_CREATE_TEMPLATE = 'CONSTRAINT "{index_name}" UNIQUE ({fields})'
    GENERATED_PK_TEMPLATE = '"{field_name}" {generated_sql}{comment}'
    FK_TEMPLATE = ' REFERENCES "{table}" ("{field}") ON DELETE {on_delete}{comment}'
    M2M_TABLE_TEMPLATE = (
        'CREATE TABLE "{table_name}" (\n'
        '    "{backward_key}" {backward_type} NOT NULL REFERENCES "{backward_table}"'
        ' ("{backward_field}") ON DELETE CASCADE,\n'
        '    "{forward_key}" {forward_type} NOT NULL REFERENCES "{forward_table}"'
        ' ("{forward_field}") ON DELETE CASCADE\n'
        "){extra}{comment};"
    )
    RENAME_TABLE_TEMPLATE = 'ALTER TABLE "{old_table}" RENAME TO "{new_table}"'
    DELETE_TABLE_TEMPLATE = 'DROP TABLE "{table}" CASCADE'
    ADD_FIELD_TEMPLATE = 'ALTER TABLE "{table}" ADD COLUMN {definition}'

    ALTER_FIELD_TEMPLATE = 'ALTER TABLE "{table}" {changes}'
    RENAME_FIELD_TEMPLATE = 'ALTER TABLE "{table}" RENAME COLUMN "{old_column}" TO "{new_column}"'
    ALTER_FIELD_NULL_TEMPLATE = 'ALTER COLUMN "{column}" DROP NOT NULL'
    ALTER_FIELD_NOT_NULL_TEMPLATE = 'ALTER COLUMN "{column}" SET NOT NULL'

    DELETE_FIELD_TEMPLATE = 'ALTER TABLE "{table}" DROP COLUMN "{column}" CASCADE'

    DELETE_CONSTRAINT_TEMPLATE = 'ALTER TABLE "{table}" DROP CONSTRAINT "{name}"'
    DELETE_FK_TEMPLATE = DELETE_CONSTRAINT_TEMPLATE
    ADD_CONSTRAINT_TEMPLATE = 'ALTER TABLE "{table}" ADD {constraint}'
    DROP_INDEX_TEMPLATE = 'DROP INDEX "{name}"'
    RENAME_INDEX_TEMPLATE: str | None = 'ALTER INDEX "{old_name}" RENAME TO "{new_name}"'
    RENAME_CONSTRAINT_TEMPLATE = (
        'ALTER TABLE "{table}" RENAME CONSTRAINT "{old_name}" TO "{new_name}"'
    )

    def __init__(
        self, connection: BaseDBAsyncClient, atomic: bool = True, collect_sql: bool = False
    ) -> None:
        self.client = connection
        self.atomic = atomic
        self.atomic_migration = connection.capabilities.can_rollback_ddl and atomic
        self.collect_sql = collect_sql
        self.collected_sql: list[str] = []

    async def _run_sql(self, sql: str) -> None:
        """Execute DDL SQL. Subclasses may override for backend-specific handling.

        If ``collect_sql`` is True, append the SQL to ``collected_sql`` instead
        of executing it.
        """
        if self.collect_sql:
            self.collected_sql.append(sql)
            return
        await self.client.execute_script(sql)

    def _get_table_comment_sql(self, table: str, comment: str) -> str:
        # Databases have their own way of supporting comments for table level
        raise NotImplementedError()  # pragma: nocoverage

    def _get_column_comment_sql(self, table: str, column: str, comment: str) -> str:
        # Databases have their own way of supporting comments for column level
        raise NotImplementedError()  # pragma: nocoverage

    def _table_generate_extra(self, table: str) -> str:
        return ""

    def _post_table_hook(self) -> str:
        return ""

    def _get_field_sql(
        self,
        db_field: str,
        field_type: str,
        nullable: bool,
        unique: bool,
        is_pk: bool,
        comment: str,
    ) -> str:
        unique_string = "UNIQUE" if unique else ""

        return self.FIELD_TEMPLATE.format(
            name=db_field,
            type=field_type,
            nullable="NOT NULL" if not nullable else "",
            unique="" if is_pk else unique_string,
            comment=comment if self.client.capabilities.inline_comment else "",
            primary=" PRIMARY KEY" if is_pk else "",
        ).strip()

    def _get_fk_reference_string(
        self,
        constraint_name: str,
        db_field: str,
        table: str,
        field: str,
        on_delete: str,
        comment: str,
    ) -> str:
        return self.FK_TEMPLATE.format(
            db_field=db_field,
            table=table,
            field=field,
            on_delete=on_delete,
            comment=comment,
        )

    @classmethod
    def _get_escape_translation_table(cls) -> list[str]:
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
        return comment.translate(self._get_escape_translation_table())

    @staticmethod
    def _make_hash(*args: str, length: int) -> str:
        return sha256(";".join(args).encode("utf-8")).hexdigest()[:length]

    def _generate_fk_name(
        self, from_table: str, from_field: str, to_table: str, to_field: str
    ) -> str:
        index_name = f"fk_{from_table[:8]}_{to_table[:8]}_{self._make_hash(from_table, from_field, to_table, to_field, length=8)}"
        return index_name

    def _generate_index_name(self, prefix: str, model: type[Model], field_names: list[str]) -> str:
        table_name = model._meta.db_table
        index_name = f"{prefix}_{table_name[:11]}_{field_names[0][:7]}_{self._make_hash(table_name, *field_names, length=6)}"
        return index_name

    def _generate_index_name_for_table(
        self, prefix: str, table_name: str, field_names: list[str]
    ) -> str:
        return f"{prefix}_{table_name[:11]}_{field_names[0][:7]}_{self._make_hash(table_name, *field_names, length=6)}"

    @staticmethod
    def quote(val: str) -> str:
        return f'"{val}"'

    @staticmethod
    def _is_index_expression(field: str) -> bool:
        return any(token in field for token in ("(", ")", " ", '"', ".", ":"))

    def _format_index_fields(self, field_names: list[str]) -> str:
        return ", ".join(
            field if self._is_index_expression(field) else self.quote(field)
            for field in field_names
        )

    def _get_unique_constraint_sql(self, model: type[Model], field_names: list[str]) -> str:
        return self.UNIQUE_CONSTRAINT_CREATE_TEMPLATE.format(
            index_name=self._generate_index_name("uid", model, field_names),
            fields=", ".join([self.quote(f) for f in field_names]),
        )

    def _get_unique_constraint_name(self, model: type[Model], field_names: list[str]) -> str:
        return self._generate_index_name("uid", model, field_names)

    def _get_index_sql(
        self,
        model: type[Model],
        field_names: list[str],
        safe: bool = False,
        index_name: str | None = None,
        index_type: str | None = None,
        extra: str | None = None,
    ) -> str:
        return self.INDEX_CREATE_TEMPLATE.format(
            index_name=index_name or self._generate_index_name("idx", model, field_names),
            table_name=model._meta.db_table,
            fields=self._format_index_fields(field_names),
            index_type=f"{index_type} " if index_type else "",
            extra=f"{extra}" if extra else "",
        )

    def _get_unique_index_sql(self, table_name: str, field_names: list[str]) -> str:
        return self.UNIQUE_INDEX_CREATE_TEMPLATE.format(
            index_name=self._generate_index_name_for_table("uidx", table_name, field_names),
            table_name=table_name,
            fields=", ".join([self.quote(f) for f in field_names]),
            extra="",
        )

    def _get_inner_statements(self) -> list[str]:
        return []

    def _get_m2m_table_definition(
        self, model: type[Model], field: ManyToManyFieldInstance
    ) -> str | None:
        if field._generated:
            return None
        related_model = field.related_model
        if not related_model:
            return None
        m2m_create_string = self.M2M_TABLE_TEMPLATE.format(
            table_name=field.through,
            backward_table=model._meta.db_table,
            forward_table=related_model._meta.db_table,
            backward_field=model._meta.db_pk_column,
            forward_field=related_model._meta.db_pk_column,
            backward_key=field.backward_key,
            backward_type=model._meta.pk.get_for_dialect(self.DIALECT, "SQL_TYPE"),
            forward_key=field.forward_key,
            forward_type=related_model._meta.pk.get_for_dialect(self.DIALECT, "SQL_TYPE"),
            extra=self._table_generate_extra(table=field.through),
            comment=self._get_table_comment_sql(table=field.through, comment=field.description)
            if field.description
            else "",
        )
        m2m_create_string += self._post_table_hook()
        if field.unique:
            unique_index_sql = self._get_unique_index_sql(
                field.through, [field.backward_key, field.forward_key]
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

    def _get_fk_field_definition(self, model: type[Model], key_field_name: str) -> str:
        key_field = model._meta.fields_map[key_field_name]
        fk_field = cast(ForeignKeyFieldInstance, key_field.reference)
        db_field = model._meta.fields_db_projection[key_field_name]
        comment = (
            self._get_column_comment_sql(
                table=model._meta.db_table, column=db_field, comment=fk_field.description
            )
            if fk_field.description
            else ""
        )

        to_field_name = fk_field.to_field_instance.source_field
        if not to_field_name:
            to_field_name = fk_field.to_field_instance.model_field_name

        field_creation_string = self._get_field_sql(
            db_field=db_field,
            field_type=key_field.get_for_dialect(self.DIALECT, "SQL_TYPE"),
            nullable=key_field.null,
            unique=key_field.unique,
            is_pk=key_field.pk,
            comment="",
        ) + self._get_fk_reference_string(
            constraint_name=self._generate_fk_name(
                model._meta.db_table,
                db_field,
                fk_field.related_model._meta.db_table,
                to_field_name,
            ),
            db_field=db_field,
            table=fk_field.related_model._meta.db_table,
            field=to_field_name,
            on_delete=fk_field.on_delete,
            comment=comment,
        )
        return field_creation_string

    def _get_model_sql_data(self, model: type[Model]) -> ModelSqlData:
        in_table_definitions: list[str] = []
        fields_with_index: list[str] = []
        m2m_tables_for_create: list[str] = []
        references = set()

        for field_name, db_field in model._meta.fields_db_projection.items():
            field_object = model._meta.fields_map[field_name]
            comment = (
                self._get_column_comment_sql(
                    table=model._meta.db_table,
                    column=db_field,
                    comment=field_object.description,
                )
                if field_object.description
                else ""
            )
            if field_object.pk and field_object.generated:
                generated_sql = field_object.get_for_dialect(self.DIALECT, "GENERATED_SQL")
                if generated_sql:
                    in_table_definitions.append(
                        self.GENERATED_PK_TEMPLATE.format(
                            field_name=db_field,
                            generated_sql=generated_sql,
                            comment=comment,
                        )
                    )
                    continue
            if field_object.generated and not field_object.pk:
                generated_sql = field_object.get_for_dialect(self.DIALECT, "GENERATED_SQL")
                if generated_sql:
                    field_creation_string = self._get_field_sql(
                        db_field=db_field,
                        field_type=f"{field_object.get_for_dialect(self.DIALECT, 'SQL_TYPE')} {generated_sql}",
                        nullable=field_object.null,
                        unique=field_object.unique,
                        is_pk=False,
                        comment=comment,
                    )
                    in_table_definitions.append(field_creation_string)
                    if field_object.index and not field_object.pk:
                        fields_with_index.append(db_field)
                    continue

            if hasattr(field_object, "reference") and field_object.reference:
                field_creation_string = self._get_fk_field_definition(model, field_name)
                reference = cast(ForeignKeyFieldInstance, field_object.reference)
                references.add(reference.related_model._meta.db_table)
            else:
                field_creation_string = self._get_field_sql(
                    db_field=db_field,
                    field_type=field_object.get_for_dialect(self.DIALECT, "SQL_TYPE"),
                    nullable=field_object.null,
                    unique=field_object.unique,
                    is_pk=field_object.pk,
                    comment=comment,
                )

            in_table_definitions.append(field_creation_string)

            if field_object.index and not field_object.pk:
                fields_with_index.append(db_field)

        if model._meta.unique_together:
            for unique_together_list in model._meta.unique_together:
                unique_together_to_create: list[str] = []

                for field in unique_together_list:
                    field_object = model._meta.fields_map[field]
                    unique_together_to_create.append(field_object.source_field or field)

                in_table_definitions.append(
                    self._get_unique_constraint_sql(model, unique_together_to_create)
                )

        _indexes = [self._get_index_sql(model, [field_name]) for field_name in fields_with_index]

        if model._meta.indexes:
            for index in model._meta.indexes:
                if isinstance(index, Index):
                    index_sql = self._get_index_sql(
                        model,
                        index.field_names,
                        index_name=index.name,
                        index_type=index.INDEX_TYPE,
                        extra=index.extra,
                    )
                    if index_sql:
                        _indexes.append(index_sql)
                    continue

                indexes_to_create: list[str] = []
                for field in index:
                    field_object = model._meta.fields_map[field]
                    indexes_to_create.append(field_object.source_field or field)

                _indexes.append(self._get_index_sql(model, indexes_to_create))

        field_indexes_sqls = [val for val in list(dict.fromkeys(_indexes)) if val]

        in_table_definitions.extend(self._get_inner_statements())

        table_fields_string = "\n    {}\n".format(",\n    ".join(in_table_definitions))
        table_comment = (
            self._get_table_comment_sql(
                table=model._meta.db_table, comment=model._meta.table_description
            )
            if model._meta.table_description
            else ""
        )

        table_create_string = self.TABLE_CREATE_TEMPLATE.format(
            table_name=model._meta.db_table,
            fields=table_fields_string,
            comment=table_comment,
            extra=self._table_generate_extra(table=model._meta.db_table),
        )

        table_create_string = "\n".join([table_create_string, *field_indexes_sqls])

        table_create_string += self._post_table_hook()

        for m2m_field in model._meta.m2m_fields:
            m2m_field_obj = cast(ManyToManyFieldInstance, model._meta.fields_map[m2m_field])
            m2m_create_string = self._get_m2m_table_definition(model, m2m_field_obj)
            if m2m_create_string:
                m2m_tables_for_create.append(m2m_create_string)

        return ModelSqlData(
            table=model._meta.db_table,
            model=model,
            table_sql=table_create_string,
            references=references,
            m2m_tables_sql=m2m_tables_for_create,
        )

    async def create_model(self, model: type[Model]) -> None:
        model_sql_data = self._get_model_sql_data(model)

        model_statement = "\n".join([model_sql_data.table_sql, *model_sql_data.m2m_tables_sql])
        await self._run_sql(model_statement)

    async def rename_table(self, model: type[Model], old_name: str, new_name: str) -> None:
        if old_name == new_name:
            return

        await self._run_sql(
            self.RENAME_TABLE_TEMPLATE.format(old_table=old_name, new_table=new_name)
        )

    async def delete_model(self, model: type[Model]) -> None:
        for field_name in model._meta.m2m_fields:
            field = cast(ManyToManyFieldInstance, model._meta.fields_map[field_name])
            await self._run_sql(self.DELETE_TABLE_TEMPLATE.format(table=field.through))

        await self._run_sql(self.DELETE_TABLE_TEMPLATE.format(table=model._meta.db_table))

    async def add_field(self, model: type[Model], field_name: str) -> None:
        field = model._meta.fields_map[field_name]
        if isinstance(field, ManyToManyFieldInstance):
            table_string = self._get_m2m_table_definition(model, field)
            if table_string:
                await self._run_sql(table_string)
            return

        if isinstance(field, ForeignKeyFieldInstance):
            key_field_name = field.source_field or field_name
            field_definition = self._get_fk_field_definition(model, key_field_name)
        else:
            db_field = model._meta.fields_db_projection[field_name]
            comment = (
                self._get_column_comment_sql(
                    table=model._meta.db_table, column=db_field, comment=field.description
                )
                if field.description
                else ""
            )

            if field.generated and not field.pk:
                generated_sql = field.get_for_dialect(self.DIALECT, "GENERATED_SQL")
            else:
                generated_sql = None

            field_type = field.get_for_dialect(self.DIALECT, "SQL_TYPE")
            if generated_sql:
                field_type = f"{field_type} {generated_sql}"

            field_definition = self._get_field_sql(
                db_field=db_field,
                field_type=field_type,
                nullable=field.null,
                unique=field.unique,
                is_pk=field.pk,
                comment=comment,
            )

        await self._run_sql(
            self.ADD_FIELD_TEMPLATE.format(table=model._meta.db_table, definition=field_definition)
        )

    async def _alter_m2m_field(
        self,
        model: type[Model],
        old_field: ManyToManyFieldInstance,
        new_field: ManyToManyFieldInstance,
    ) -> None:
        if old_field.through != new_field.through:
            await self._run_sql(
                self.RENAME_TABLE_TEMPLATE.format(
                    old_table=old_field.through, new_table=new_field.through
                )
            )

        if old_field.forward_key != new_field.forward_key:
            await self._run_sql(
                self.RENAME_FIELD_TEMPLATE.format(
                    table=new_field.through,
                    old_column=old_field.forward_key,
                    new_column=new_field.forward_key,
                )
            )

        if old_field.backward_key != new_field.backward_key:
            await self._run_sql(
                self.RENAME_FIELD_TEMPLATE.format(
                    table=new_field.through,
                    old_column=old_field.backward_key,
                    new_column=new_field.backward_key,
                )
            )

    async def _alter_generated_field(
        self, model: type[Model], old_field: Field, new_field: Field
    ) -> bool:
        if old_field.pk or new_field.pk:
            return False

        old_generated_sql = (
            old_field.get_for_dialect(self.DIALECT, "GENERATED_SQL")
            if old_field.generated
            else None
        )
        new_generated_sql = (
            new_field.get_for_dialect(self.DIALECT, "GENERATED_SQL")
            if new_field.generated
            else None
        )
        if old_generated_sql == new_generated_sql:
            return False
        if old_field.generated or new_field.generated:
            raise ValueError(
                f"Modifying generated fields is not supported - the field {new_field} "
                "must be removed and re-added with the new definition."
            )
        return False

    async def _alter_field(self, model: type[Model], old_field: Field, new_field: Field) -> None:
        actions: list[str] = []
        old_db_field = old_field.source_field or old_field.model_field_name
        new_db_field = new_field.source_field or new_field.model_field_name
        if await self._alter_generated_field(model, old_field, new_field):
            return
        if old_field.null != new_field.null:
            if new_field.null:
                changes = self.ALTER_FIELD_NULL_TEMPLATE.format(column=old_db_field)
            else:
                changes = self.ALTER_FIELD_NOT_NULL_TEMPLATE.format(column=new_db_field)

            actions.append(
                self.ALTER_FIELD_TEMPLATE.format(table=model._meta.db_table, changes=changes)
            )

        if old_field.index != new_field.index:
            index = Index(fields=(new_db_field,))
            if new_field.index:
                await self.add_index(model, index)
            else:
                await self.remove_index(model, index)

        if old_field.unique != new_field.unique:
            constraint = UniqueConstraint(fields=(new_db_field,))
            if new_field.unique:
                await self.add_constraint(model, constraint)
            else:
                await self.remove_constraint(model, constraint)

        if old_field.description != new_field.description:
            # TODO description management
            pass

        if old_db_field != new_db_field:
            actions.append(
                self.RENAME_FIELD_TEMPLATE.format(
                    table=model._meta.db_table,
                    old_column=old_db_field,
                    new_column=new_db_field,
                )
            )

        if not actions:
            return
        result_query = ";\n".join(actions)
        await self._run_sql(result_query)

    async def alter_field(
        self, old_model: type[Model], new_model: type[Model], field_name: str
    ) -> None:
        old_field = old_model._meta.fields_map[field_name]
        new_field = new_model._meta.fields_map[field_name]

        if old_field.field_type != new_field.field_type:
            raise ValueError(
                f"Automatic field type altering is not supported yet (field '{field_name}'). "
                f"Please use AlterFieldManual"
            )

        if isinstance(old_field, ManyToManyFieldInstance):
            new_field = cast(ManyToManyFieldInstance, new_field)
            await self._alter_m2m_field(new_model, old_field, new_field)
            return

        if isinstance(old_field, ForeignKeyFieldInstance):
            old_source = old_field.source_field or field_name
            new_source = new_field.source_field or field_name
            old_field = old_model._meta.fields_map[old_source]
            new_field = new_model._meta.fields_map[new_source]

        await self._alter_field(new_model, old_field, new_field)

    async def remove_field(self, model: type[Model], field: Field) -> None:
        if isinstance(field, ManyToManyFieldInstance):
            await self._run_sql(self.DELETE_TABLE_TEMPLATE.format(table=field.through))
            return

        if isinstance(field, ForeignKeyFieldInstance):
            source_field = field.source_field or field.model_field_name
            field = model._meta.fields_map[source_field]
            # TODO Drop constraints as they can block field drop
        db_field = model._meta.fields_db_projection.get(
            field.model_field_name, field.source_field or field.model_field_name
        )
        await self._run_sql(
            self.DELETE_FIELD_TEMPLATE.format(table=model._meta.db_table, column=db_field)
        )

    def _index_name_for_model(self, model: type[Model], index: Index) -> str:
        if index.name:
            return index.name
        index.resolve_expressions(model)
        return self._generate_index_name("idx", model, list(index.field_names))

    def _constraint_name_for_model(self, model: type[Model], constraint: UniqueConstraint) -> str:
        if constraint.name:
            return constraint.name
        return self._get_unique_constraint_name(model, list(constraint.fields))

    async def add_index(self, model: type[Model], index: Index) -> None:
        index.resolve_expressions(model)
        index_sql = self._get_index_sql(
            model,
            list(index.field_names),
            index_name=self._index_name_for_model(model, index),
            index_type=index.INDEX_TYPE,
            extra=index.extra,
        )
        if index_sql:
            await self._run_sql(index_sql)

    async def remove_index(self, model: type[Model], index: Index) -> None:
        index_name = self._index_name_for_model(model, index)
        await self._run_sql(
            self.DROP_INDEX_TEMPLATE.format(name=index_name, table=model._meta.db_table)
        )

    async def rename_index(self, model: type[Model], old_index: Index, new_index: Index) -> None:
        old_name = self._index_name_for_model(model, old_index)
        new_name = self._index_name_for_model(model, new_index)
        if old_name == new_name:
            return
        if self.RENAME_INDEX_TEMPLATE:
            await self._run_sql(
                self.RENAME_INDEX_TEMPLATE.format(
                    table=model._meta.db_table, old_name=old_name, new_name=new_name
                )
            )
            return
        await self.remove_index(model, old_index)
        await self.add_index(model, new_index)

    async def add_constraint(self, model: type[Model], constraint: UniqueConstraint) -> None:
        constraint_name = self._constraint_name_for_model(model, constraint)
        constraint_sql = self.UNIQUE_CONSTRAINT_CREATE_TEMPLATE.format(
            index_name=constraint_name,
            fields=", ".join([self.quote(f) for f in constraint.fields]),
        )
        await self._run_sql(
            self.ADD_CONSTRAINT_TEMPLATE.format(
                table=model._meta.db_table, constraint=constraint_sql
            )
        )

    async def remove_constraint(self, model: type[Model], constraint: UniqueConstraint) -> None:
        constraint_name = self._constraint_name_for_model(model, constraint)
        await self._run_sql(
            self.DELETE_CONSTRAINT_TEMPLATE.format(table=model._meta.db_table, name=constraint_name)
        )

    async def rename_constraint(
        self, model: type[Model], old_constraint: UniqueConstraint, new_constraint: UniqueConstraint
    ) -> None:
        old_name = self._constraint_name_for_model(model, old_constraint)
        new_name = self._constraint_name_for_model(model, new_constraint)
        if old_name == new_name:
            return
        if self.RENAME_CONSTRAINT_TEMPLATE:
            await self._run_sql(
                self.RENAME_CONSTRAINT_TEMPLATE.format(
                    table=model._meta.db_table, old_name=old_name, new_name=new_name
                )
            )
            return
        await self.remove_constraint(model, old_constraint)
        await self.add_constraint(model, new_constraint)
