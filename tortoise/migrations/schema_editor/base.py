from _sha256 import sha256
from typing import Type, cast, List, Optional

from tortoise.fields.relational import ManyToManyFieldInstance, ForeignKeyFieldInstance

from tortoise.fields.base import Field

from tortoise.models import Model

from tortoise.backends.base.client import BaseDBAsyncClient
from tortoise.migrations.schema_editor.data import ModelSqlData


class BaseSchemaEditor:
    DIALECT = "sql"
    TABLE_CREATE_TEMPLATE = 'CREATE TABLE "{table_name}" ({fields}){extra}{comment};'
    FIELD_TEMPLATE = '"{name}" {type} {nullable} {unique}{primary}{comment}'
    INDEX_CREATE_TEMPLATE = 'CREATE INDEX "{index_name}" ON "{table_name}" ({fields});'
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
    RENAME_FIELD_TEMPLATE = (
        'ALTER TABLE "{table}" RENAME COLUMN "{old_column}" TO "{new_column}"'
    )
    ALTER_FIELD_NULL_TEMPLATE = 'ALTER COLUMN "{column}" DROP NOT NULL'
    ALTER_FIELD_NOT_NULL_TEMPLATE = 'ALTER COLUMN "{column}" SET NOT NULL'

    DELETE_FIELD_TEMPLATE = 'ALTER TABLE "{table}" DROP COLUMN "{column}" CASCADE'

    DELETE_CONSTRAINT_TEMPLATE = 'ALTER TABLE "{table}" DROP CONSTRAINT "{name}"'
    DELETE_FK_TEMPLATE = DELETE_CONSTRAINT_TEMPLATE

    def __init__(self, connection: BaseDBAsyncClient):
        self.client = connection

    def _get_table_comment_sql(self, table: str, comment: str) -> str:
        # Databases have their own way of supporting comments for table level
        # needs to be implemented for each supported client
        raise NotImplementedError()  # pragma: nocoverage

    def _get_column_comment_sql(self, table: str, column: str, comment: str) -> str:
        # Databases have their own way of supporting comments for column level
        # needs to be implemented for each supported client
        raise NotImplementedError()  # pragma: nocoverage

    def _table_generate_extra(self, table: str) -> str:
        return ""

    def _post_table_hook(self) -> str:
        # This method provides a mechanism where you can perform a set of
        # operation on the database table after  it's initialized. This method
        # by default does nothing. If need be, it can be over-written
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
        # children can override this function to customize their sql queries
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

    @staticmethod
    def _make_hash(*args: str, length: int) -> str:
        # Hash a set of string values and get a digest of the given length.
        return sha256(";".join(args).encode("utf-8")).hexdigest()[:length]

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

    def _generate_index_name(
        self, prefix: str, model: "Type[Model]", field_names: List[str]
    ) -> str:
        # NOTE: for compatibility, index name should not be longer than 30
        # characters (Oracle limit).
        # That's why we slice some of the strings here.
        table_name = model._meta.table
        index_name = "{}_{}_{}_{}".format(
            prefix,
            table_name[:11],
            field_names[0][:7],
            self._make_hash(table_name, *field_names, length=6),
        )
        return index_name

    @staticmethod
    def quote(val: str) -> str:
        return f'"{val}"'

    def _get_unique_constraint_sql(
        self, model: "Type[Model]", field_names: List[str]
    ) -> str:
        return self.UNIQUE_CONSTRAINT_CREATE_TEMPLATE.format(
            index_name=self._generate_index_name("uid", model, field_names),
            fields=", ".join([self.quote(f) for f in field_names]),
        )

    def _get_index_sql(self, model: "Type[Model]", field_names: List[str]) -> str:
        return self.INDEX_CREATE_TEMPLATE.format(
            index_name=self._generate_index_name("idx", model, field_names),
            table_name=model._meta.table,
            fields=", ".join([self.quote(f) for f in field_names]),
        )

    def _get_inner_statements(self) -> List[str]:
        return []

    def _get_m2m_table_definition(
        self, model: Type[Model], field: ManyToManyFieldInstance
    ) -> Optional[str]:
        if field._generated:
            return
        m2m_create_string = self.M2M_TABLE_TEMPLATE.format(
            table_name=field.through,
            backward_table=model._meta.table,
            forward_table=field.model_class._meta.table,
            backward_field=model._meta.db_pk_field,
            forward_field=field.model_class._meta.db_pk_field,
            backward_key=field.backward_key,
            backward_type=model._meta.pk.get_for_dialect(self.DIALECT, "SQL_TYPE"),
            forward_key=field.forward_key,
            forward_type=field.model_class._meta.pk.get_for_dialect(
                self.DIALECT, "SQL_TYPE"
            ),
            extra=self._table_generate_extra(table=field.through),
            comment=self._get_table_comment_sql(
                table=field.through, comment=field.description
            )
            if field.description
            else "",
        )
        m2m_create_string += self._post_table_hook()

    def _get_fk_field_definition(self, model: Type[Model], key_field_name: str) -> str:
        key_field = model._meta.fields_map[key_field_name]
        fk_field = cast("ForeignKeyFieldInstance", key_field.reference)
        db_field = model._meta.fields_db_projection[key_field_name]
        comment = (
            self._get_column_comment_sql(
                table=model._meta.table, column=db_field, comment=fk_field.description,
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
                model._meta.table,
                db_field,
                fk_field.model_class._meta.table,
                to_field_name,
            ),
            db_field=db_field,
            table=fk_field.model_class._meta.table,
            field=to_field_name,
            on_delete=fk_field.on_delete,
            comment=comment,
        )
        return field_creation_string

    def _get_model_sql_data(self, model: "Type[Model]") -> ModelSqlData:
        in_table_definitions = []
        fields_with_index = []
        m2m_tables_for_create = []
        references = set()

        for field_name, db_field in model._meta.fields_db_projection.items():
            field_object = model._meta.fields_map[field_name]
            comment = (
                self._get_column_comment_sql(
                    table=model._meta.table,
                    column=db_field,
                    comment=field_object.description,
                )
                if field_object.description
                else ""
            )
            # TODO: PK generation needs to move out of schema generator.
            if field_object.pk:
                if field_object.generated:
                    generated_sql = field_object.get_for_dialect(
                        self.DIALECT, "GENERATED_SQL"
                    )
                    if generated_sql:  # pragma: nobranch
                        in_table_definitions.append(
                            self.GENERATED_PK_TEMPLATE.format(
                                field_name=db_field,
                                generated_sql=generated_sql,
                                comment=comment,
                            )
                        )
                        continue

            if hasattr(field_object, "reference") and field_object.reference:
                field_creation_string = self._get_fk_field_definition(model, field_name)
                reference = cast("ForeignKeyFieldInstance", field_object.reference)
                references.add(reference.model_class._meta.table)
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
                unique_together_to_create = []

                for field in unique_together_list:
                    field_object = model._meta.fields_map[field]
                    unique_together_to_create.append(field_object.source_field or field)

                in_table_definitions.append(
                    self._get_unique_constraint_sql(model, unique_together_to_create)
                )

        # Indexes.
        _indexes = [
            self._get_index_sql(model, [field_name]) for field_name in fields_with_index
        ]

        if model._meta.indexes:
            for indexes_list in model._meta.indexes:
                indexes_to_create = []
                for field in indexes_list:
                    field_object = model._meta.fields_map[field]
                    indexes_to_create.append(field_object.source_field or field)

                _indexes.append(self._get_index_sql(model, indexes_to_create))

        field_indexes_sqls = [val for val in list(dict.fromkeys(_indexes)) if val]

        in_table_definitions.extend(self._get_inner_statements())

        table_fields_string = "\n    {}\n".format(",\n    ".join(in_table_definitions))
        table_comment = (
            self._get_table_comment_sql(
                table=model._meta.table, comment=model._meta.table_description
            )
            if model._meta.table_description
            else ""
        )

        table_create_string = self.TABLE_CREATE_TEMPLATE.format(
            table_name=model._meta.table,
            fields=table_fields_string,
            comment=table_comment,
            extra=self._table_generate_extra(table=model._meta.table),
        )

        table_create_string = "\n".join([table_create_string, *field_indexes_sqls])

        table_create_string += self._post_table_hook()

        for m2m_field in model._meta.m2m_fields:
            m2m_create_string = self._get_m2m_table_definition(model, m2m_field)
            if m2m_create_string:
                m2m_tables_for_create.append(m2m_create_string)

        return ModelSqlData(
            table=model._meta.table,
            model=model,
            table_sql=table_create_string,
            references=references,
            m2m_tables_sql=m2m_tables_for_create,
        )

    async def create_model(self, model: Type[Model]):
        model_sql_data = self._get_model_sql_data(model)

        model_statement = "\n".join(
            [model_sql_data.table_sql, *model_sql_data.m2m_tables_sql]
        )
        await self.client.execute_script(model_statement)

    async def rename_table(self, model: Type[Model], old_name: str, new_name: str):
        if old_name == new_name:
            return

        await self.client.execute_script(
            self.RENAME_TABLE_TEMPLATE.format(old_table=old_name, new_table=new_name)
        )

    async def delete_model(self, model: Type[Model]):
        for field_name in model._meta.m2m_fields:
            field = cast(ManyToManyFieldInstance, model._meta.fields_map[field_name])
            await self.client.execute_script(
                self.DELETE_TABLE_TEMPLATE.format(table=field.through)
            )

        await self.client.execute_script(
            self.DELETE_TABLE_TEMPLATE.format(table=model._meta.table)
        )

    async def add_field(self, model: Type[Model], field_name: str):
        field = model._meta.fields_map[field_name]
        db_field = model._meta.fields_db_projection[field_name]
        if isinstance(field, ManyToManyFieldInstance):
            table_string = self._get_m2m_table_definition(model, field)
            await self.client.execute_script(table_string)
            return

        if isinstance(field, ForeignKeyFieldInstance):
            field_definition = self._get_fk_field_definition(model, field.source_field)
        else:
            comment = (
                self._get_column_comment_sql(
                    table=model._meta.table, column=db_field, comment=field.description,
                )
                if field.description
                else ""
            )

            field_definition = self._get_field_sql(
                db_field=db_field,
                field_type=field.get_for_dialect(self.DIALECT, "SQL_TYPE"),
                nullable=field.null,
                unique=field.unique,
                is_pk=field.pk,
                comment=comment,
            )

        await self.client.execute_script(
            self.ADD_FIELD_TEMPLATE.format(
                table=model._meta.table, definition=field_definition
            )
        )

    async def _alter_m2m_field(
        self,
        model: Type[Model],
        old_field: ManyToManyFieldInstance,
        new_field: ManyToManyFieldInstance,
    ):
        if old_field.through != new_field.through:
            await self.client.execute_script(
                self.RENAME_TABLE_TEMPLATE.format(
                    old_table=old_field.through, new_table=new_field.through
                )
            )

        if old_field.forward_key != new_field.forward_key:
            await self.client.execute_script(
                self.RENAME_FIELD_TEMPLATE.format(
                    table=new_field.through,
                    old_column=old_field.forward_key,
                    new_column=new_field.forward_key,
                )
            )

        if old_field.backward_key != new_field.backward_key:
            await self.client.execute_script(
                self.RENAME_FIELD_TEMPLATE.format(
                    table=new_field.through,
                    old_column=old_field.backward_key,
                    new_column=new_field.backward_key,
                )
            )

    async def _alter_field(
        self, model: Type[Model], old_field: Field, new_field: Field
    ):
        actions = []
        if old_field.null != new_field.null:
            if new_field.null:
                changes = self.ALTER_FIELD_NULL_TEMPLATE.format(
                    column=old_field.source_field
                )
            else:
                changes = self.ALTER_FIELD_NOT_NULL_TEMPLATE.format(
                    column=new_field.source_field
                )

            actions.append(
                self.ALTER_FIELD_TEMPLATE.format(
                    table=model._meta.table, changes=changes
                )
            )

        if old_field.index != new_field.index:
            # TODO Index management
            pass

        if old_field.unique != new_field.index:
            # TODO Index management
            pass

        if old_field.description != new_field.description:
            # TODO description management
            pass

        if old_field.source_field != new_field.source_field:
            actions.append(
                self.RENAME_FIELD_TEMPLATE.format(
                    table=model._meta.table,
                    old_column=old_field.source_field,
                    new_column=new_field.source_field,
                )
            )

        result_query = ";\n".join(actions)
        await self.client.execute_script(result_query)

    async def alter_field(
        self, old_model: Type[Model], new_model: Type[Model], field_name: str,
    ):
        old_field = old_model._meta.fields_map[field_name]
        new_field = new_model._meta.fields_map[field_name]

        if old_field.field_type != new_field.field_type:
            # TODO Add operation for manual altering
            raise ValueError(
                f"Automatic field type altering is not supported yet (field '{field_name}'). "
                f"Please use AlterFieldManual"
            )

        if isinstance(old_field, ManyToManyFieldInstance):
            new_field = cast(ManyToManyFieldInstance, new_field)
            await self._alter_m2m_field(new_model, old_field, new_field)
            return

        if isinstance(old_field, ForeignKeyFieldInstance):
            old_field = old_model._meta.fields_map[old_field.source_field]
            new_field = new_model._meta.fields_map[new_field.source_field]

        await self._alter_field(new_model, old_field, new_field)

    async def remove_field(self, model: Type[Model], field: Field):
        if isinstance(field, ManyToManyFieldInstance):
            field = cast(ManyToManyFieldInstance, field)
            await self.client.execute_script(
                self.DELETE_TABLE_TEMPLATE.format(table=field.through)
            )
            return

        if isinstance(field, ForeignKeyFieldInstance):
            field = model._meta.fields_map[field.source_field]
            # TODO Drop constraints as they can block field drop

        await self.client.execute_script(
            self.DELETE_FIELD_TEMPLATE.format(
                table=model._meta.table, column=field.source_field
            )
        )
