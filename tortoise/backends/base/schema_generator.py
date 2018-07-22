from typing import List, Set  # noqa

from tortoise import fields
from tortoise.exceptions import ConfigurationError


class BaseSchemaGenerator:
    TABLE_CREATE_TEMPLATE = 'CREATE TABLE "{}" ({});'
    FIELD_TEMPLATE = '"{name}" {type} {nullable} {unique}'
    FK_TEMPLATE = ' REFERENCES "{table}" (id) ON DELETE {on_delete}'
    M2M_TABLE_TEMPLATE = (
        'CREATE TABLE "{table_name}" '
        '("{backward_key}" INT NOT NULL REFERENCES "{backward_table}" (id) ON DELETE CASCADE, '
        '"{forward_key}" INT NOT NULL REFERENCES "{forward_table}" (id) ON DELETE CASCADE);'
    )

    FIELD_TYPE_MAP = {
        fields.BooleanField: 'BOOL',
        fields.IntField: 'INT',
        fields.SmallIntField: 'SMALLINT',
        fields.TextField: 'TEXT',
        fields.CharField: 'VARCHAR({})',
        fields.DatetimeField: 'TIMESTAMP',
        fields.DecimalField: 'DECIMAL({},{})',
        fields.DateField: 'DATE',
        fields.FloatField: 'DOUBLE PRECISION',
        fields.JSONField: 'TEXT'
    }

    def __init__(self, client):
        self.client = client

    def _create_string(self, db_field, field_type, nullable, unique):
        # children can override this function to customize thier sql queries

        field_creation_string = self.FIELD_TEMPLATE.format(
            name=db_field,
            type=field_type,
            nullable=nullable,
            unique=unique,
        ).strip()

        return field_creation_string

    def _get_primary_key_create_string(self, field_name):
        # All databases have their unique way for autoincrement,
        # has to implement in children
        raise NotImplementedError()  # pragma: nocoverage

    def _get_auto_now_add_default(self):
        raise NotImplementedError()  # pragma: nocoverage

    def _get_table_sql(self, model) -> dict:
        fields_to_create = []
        m2m_tables_for_create = []
        references = set()
        for field_name, db_field in model._meta.fields_db_projection.items():
            field_object = model._meta.fields_map[field_name]
            if isinstance(field_object, fields.IntField) and field_object.pk:
                fields_to_create.append(self._get_primary_key_create_string(field_name))
                continue
            nullable = 'NOT NULL' if not field_object.null else ''
            unique = 'UNIQUE' if field_object.unique else ''

            field_type = self.FIELD_TYPE_MAP[field_object.__class__]
            if isinstance(field_object, fields.DecimalField):
                field_type = field_type.format(field_object.max_digits, field_object.decimal_places)
            elif isinstance(field_object, fields.CharField):
                field_type = field_type.format(field_object.max_length)

            field_creation_string = self._create_string(db_field, field_type, nullable, unique)

            if hasattr(field_object, 'reference') and field_object.reference:
                field_creation_string += self.FK_TEMPLATE.format(
                    table=field_object.reference.type._meta.table,
                    on_delete=field_object.reference.on_delete,
                )
                references.add(field_object.reference.type._meta.table)
            fields_to_create.append(field_creation_string)

        table_fields_string = ', '.join(fields_to_create)
        table_create_string = self.TABLE_CREATE_TEMPLATE.format(
            model._meta.table,
            table_fields_string,
        )

        for m2m_field in model._meta.m2m_fields:
            field_object = model._meta.fields_map[m2m_field]
            if field_object._generated:
                continue
            m2m_tables_for_create.append(
                self.M2M_TABLE_TEMPLATE.format(
                    table_name=field_object.through,
                    backward_table=model._meta.table,
                    forward_table=field_object.type._meta.table,
                    backward_key=field_object.backward_key,
                    forward_key=field_object.forward_key,
                )
            )

        return {
            'table': model._meta.table,
            'model': model,
            'table_creation_string': table_create_string,
            'references': references,
            'm2m_tables': m2m_tables_for_create,
        }

    def get_create_schema_sql(self):
        from tortoise import Tortoise
        models_to_create = []

        for app in Tortoise.apps.values():
            for model in app.values():
                if model._meta.db == self.client:
                    models_to_create.append(model)

        tables_to_create = []
        for model in models_to_create:
            tables_to_create.append(self._get_table_sql(model))

        tables_to_create_count = len(tables_to_create)

        created_tables = set()  # type: Set[dict]
        ordered_tables_for_create = []
        m2m_tables_to_create = []  # type: List[str]
        while True:
            if len(created_tables) == tables_to_create_count:
                break
            try:
                next_table_for_create = next(
                    t for t in tables_to_create if t['references'].issubset(created_tables)
                )
            except StopIteration:
                raise ConfigurationError("Can't create schema due to cyclic fk references")
            tables_to_create.remove(next_table_for_create)
            created_tables.add(next_table_for_create['table'])
            ordered_tables_for_create.append(next_table_for_create['table_creation_string'])
            m2m_tables_to_create += next_table_for_create['m2m_tables']

        schema_creation_string = ' '.join(ordered_tables_for_create + m2m_tables_to_create)
        return schema_creation_string

    async def generate_from_string(self, creation_string):
        await self.client.execute_script(creation_string)
