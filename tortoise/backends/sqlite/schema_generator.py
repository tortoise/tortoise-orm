from tortoise import fields
from tortoise.backends.base.schema_generator import BaseSchemaGenerator


class SqliteSchemaGenerator(BaseSchemaGenerator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.FIELD_TYPE_MAP.update({
            fields.BooleanField: 'INTEGER',
            fields.FloatField: 'REAL',
            fields.DecimalField: 'VARCHAR(40)',
        })

    def _get_primary_key_create_string(self, field_name):
        return '"{}" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL'.format(field_name)
