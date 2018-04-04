from tortoise.backends.base.schema_generator import BaseSchemaGenerator


class SqliteSchemaGenerator(BaseSchemaGenerator):
    def _get_primary_key_create_string(self, field_name):
        return '"{}" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL'.format(field_name)
