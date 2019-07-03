import warnings
from typing import List, Set  # noqa

from tortoise import fields
from tortoise.exceptions import ConfigurationError
from tortoise.utils import get_escape_translation_table


class BaseSchemaGenerator:
    TABLE_CREATE_TEMPLATE = 'CREATE TABLE {exists}"{table_name}" ({fields}) {comment};'
    FIELD_TEMPLATE = '"{name}" {type} {nullable} {unique} {comment}'
    INDEX_CREATE_TEMPLATE = 'CREATE INDEX {exists}"{index_name}" ON "{table_name}" ({fields});'
    UNIQUE_CONSTRAINT_CREATE_TEMPLATE = "UNIQUE ({fields})"
    FK_TEMPLATE = ' REFERENCES "{table}" (id) ON DELETE {on_delete}'
    M2M_TABLE_TEMPLATE = (
        'CREATE TABLE {exists}"{table_name}" ('
        '"{backward_key}" {backward_type} NOT NULL REFERENCES "{backward_table}" (id)'
        " ON DELETE CASCADE,"
        '"{forward_key}" {forward_type} NOT NULL REFERENCES "{forward_table}" (id)'
        " ON DELETE CASCADE"
        ") {comment};"
    )

    FIELD_TYPE_MAP = {
        fields.BooleanField: "BOOL",
        fields.IntField: "INT",
        fields.SmallIntField: "SMALLINT",
        fields.BigIntField: "BIGINT",
        fields.TextField: "TEXT",
        fields.CharField: "VARCHAR({})",
        fields.DatetimeField: "TIMESTAMP",
        fields.DecimalField: "DECIMAL({},{})",
        fields.TimeDeltaField: "BIGINT",
        fields.DateField: "DATE",
        fields.FloatField: "DOUBLE PRECISION",
        fields.JSONField: "TEXT",
        fields.UUIDField: "CHAR(36)",
    }

    def __init__(self, client) -> None:
        self.client = client

    def _create_string(
        self, db_field: str, field_type: str, nullable: str, unique: str, is_pk: bool, comment: str
    ) -> str:
        # children can override this function to customize thier sql queries

        field_creation_string = self.FIELD_TEMPLATE.format(
            name=db_field,
            type=field_type,
            nullable=nullable,
            unique=unique,
            comment=comment if self.client.capabilities.inline_comment else "",
        ).strip()

        if is_pk:
            field_creation_string += " PRIMARY KEY"

        return field_creation_string

    def _get_primary_key_create_string(self, field_name: str) -> str:
        # All databases have their unique way for autoincrement,
        # has to implement in children
        raise NotImplementedError()  # pragma: nocoverage

    def _table_comment_generator(self, model, comments_array: List) -> str:
        # Databases have their own way of supporting comments for table level
        # needs to be implemented for each supported client
        raise NotImplementedError()  # pragma: nocoverage

    def _column_comment_generator(self, model, field, comments_array: List) -> str:
        # Databases have their own way of supporting comments for column level
        # needs to be implemented for each supported client
        raise NotImplementedError()  # pragma: nocoverage

    def _post_table_hook(self, *, models=None, safe=True) -> str:
        # This method provides a mechanism where you can perform a set of
        # operation on the database table after  it's initialized. This method
        # by default does nothing. If need be, it can be over-written
        return ""

    def _escape_comment(self, comment: str) -> str:
        # This method provides a default method to escape comment strings as per
        # default standard as applied under mysql like database. This can be
        # overwritten if required to match the database specific escaping.
        return comment.translate(get_escape_translation_table())

    @staticmethod
    def _make_hash(*args: str, length: int) -> str:
        # Hash a set of string values and get a digest of the given length.
        letters = []  # type: List[str]
        for i_th_letters in zip(*args):
            letters.extend(i_th_letters)
        return "".join([str(ord(letter)) for letter in letters])[:length]

    def _generate_index_name(self, model, field_names: List[str]) -> str:
        # NOTE: for compatibility, index name should not be longer than 30
        # characters (Oracle limit).
        # That's why we slice some of the strings here.
        table_name = model._meta.table
        index_name = "{t}_{f}_{h}_idx".format(
            t=table_name[:11],
            f=field_names[0][:7],
            h=self._make_hash(table_name, *field_names, length=6),
        )
        return index_name

    def _get_index_sql(self, model, field_names: List[str], safe: bool) -> str:
        return self.INDEX_CREATE_TEMPLATE.format(
            exists="IF NOT EXISTS " if safe else "",
            index_name=self._generate_index_name(model, field_names),
            table_name=model._meta.table,
            fields=", ".join(field_names),
        )

    def _get_unique_constraint_sql(self, field_names: List[str]) -> str:
        return self.UNIQUE_CONSTRAINT_CREATE_TEMPLATE.format(fields=", ".join(field_names))

    def _get_field_type(self, field_object) -> str:
        field_object_type = type(field_object)
        while field_object_type.__bases__ and field_object_type not in self.FIELD_TYPE_MAP:
            field_object_type = field_object_type.__bases__[0]

        field_type = self.FIELD_TYPE_MAP[field_object_type]

        if isinstance(field_object, fields.DecimalField):
            field_type = field_type.format(field_object.max_digits, field_object.decimal_places)
        elif isinstance(field_object, fields.CharField):
            field_type = field_type.format(field_object.max_length)

        return field_type

    def _get_table_sql(self, model, safe=True) -> dict:

        fields_to_create = []
        fields_with_index = []
        m2m_tables_for_create = []
        references = set()
        comments = []  # type: List

        for field_name, db_field in model._meta.fields_db_projection.items():
            field_object = model._meta.fields_map[field_name]
            if isinstance(field_object, (fields.IntField, fields.BigIntField)) and field_object.pk:
                fields_to_create.append(self._get_primary_key_create_string(field_name))
                continue
            nullable = "NOT NULL" if not field_object.null else ""
            unique = "UNIQUE" if field_object.unique else ""
            field_creation_string = self._create_string(
                db_field=db_field,
                field_type=self._get_field_type(field_object),
                nullable=nullable,
                unique=unique,
                is_pk=field_object.pk,
                comment=self._column_comment_generator(
                    model=model, field=field_object, comments_array=comments
                ),
            )

            if hasattr(field_object, "reference") and field_object.reference:
                field_creation_string += self.FK_TEMPLATE.format(
                    table=field_object.reference.type._meta.table,
                    on_delete=field_object.reference.on_delete,
                )
                references.add(field_object.reference.type._meta.table)
            fields_to_create.append(field_creation_string)

            if field_object.index:
                fields_with_index.append(field_name)

        if model._meta.unique_together is not None:
            unique_together_sqls = []

            for unique_together_list in model._meta.unique_together:
                unique_together_to_create = []

                for field in unique_together_list:
                    field_object = model._meta.fields_map[field]

                    if field_object.source_field:
                        unique_together_to_create.append(field_object.source_field)
                    else:
                        unique_together_to_create.append(field)

                unique_together_sqls.append(
                    self._get_unique_constraint_sql(unique_together_to_create)
                )

            fields_to_create.extend(unique_together_sqls)

        table_fields_string = ", ".join(fields_to_create)
        table_comment = (
            self._table_comment_generator(model=model, comments_array=comments)
            if self.client.capabilities.inline_comment
            else ""
        )

        table_create_string = self.TABLE_CREATE_TEMPLATE.format(
            exists="IF NOT EXISTS " if safe else "",
            table_name=model._meta.table,
            fields=table_fields_string,
            comment=table_comment,
        )

        # Indexes.
        field_indexes_sqls = [
            self._get_index_sql(model, [field_name], safe=safe) for field_name in fields_with_index
        ]
        if safe and not self.client.capabilities.safe_indexes:
            warnings.warn(
                "Skipping creation of field indexes for fields {field_names} "
                'on table "{table_name}" : safe index creation is not supported yet for {dialect}. '
                "Please find the SQL queries to create the indexes below.".format(
                    field_names=", ".join(fields_with_index),
                    table_name=model._meta.table,
                    dialect=self.client.capabilities.dialect,
                )
            )
            warnings.warn("\n".join(field_indexes_sqls))
        else:
            table_create_string = " ".join([table_create_string, *field_indexes_sqls])

        if comments:
            table_create_string = " ".join([table_create_string, *comments])

        for m2m_field in model._meta.m2m_fields:
            field_object = model._meta.fields_map[m2m_field]
            if field_object._generated:
                continue
            m2m_tables_for_create.append(
                self.M2M_TABLE_TEMPLATE.format(
                    exists="IF NOT EXISTS " if safe else "",
                    table_name=field_object.through,
                    backward_table=model._meta.table,
                    forward_table=field_object.type._meta.table,
                    backward_key=field_object.backward_key,
                    backward_type=self._get_field_type(model._meta.pk),
                    forward_key=field_object.forward_key,
                    forward_type=self._get_field_type(field_object.type._meta.pk),
                    comment=table_comment,
                )
            )

        return {
            "table": model._meta.table,
            "model": model,
            "table_creation_string": table_create_string,
            "references": references,
            "m2m_tables": m2m_tables_for_create,
        }

    def _get_models_to_create(self, models_to_create) -> None:
        from tortoise import Tortoise

        for app in Tortoise.apps.values():
            for model in app.values():
                if model._meta.db == self.client:
                    model.check()
                    models_to_create.append(model)

    def get_create_schema_sql(self, safe=True) -> str:
        models_to_create = []  # type: List

        self._get_models_to_create(models_to_create)

        tables_to_create = []
        for model in models_to_create:
            tables_to_create.append(self._get_table_sql(model, safe))

        tables_to_create_count = len(tables_to_create)

        created_tables = set()  # type: Set[dict]
        ordered_tables_for_create = []
        m2m_tables_to_create = []  # type: List[str]
        while True:
            if len(created_tables) == tables_to_create_count:
                break
            try:
                next_table_for_create = next(
                    t for t in tables_to_create if t["references"].issubset(created_tables)
                )
            except StopIteration:
                raise ConfigurationError("Can't create schema due to cyclic fk references")
            tables_to_create.remove(next_table_for_create)
            created_tables.add(next_table_for_create["table"])
            ordered_tables_for_create.append(next_table_for_create["table_creation_string"])
            m2m_tables_to_create += next_table_for_create["m2m_tables"]

        schema_creation_string = " ".join(ordered_tables_for_create + m2m_tables_to_create)
        return schema_creation_string

    def generate_post_table_hook_sql(self, safe=True) -> str:
        models_to_use = []  # type: List

        self._get_models_to_create(models_to_use)
        return self._post_table_hook(models=models_to_use, safe=safe)

    async def generate_from_string(self, creation_string: str) -> None:
        # print(creation_string)
        await self.client.execute_script(creation_string)
