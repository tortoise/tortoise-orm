from tortoise.backends.base.schema_generator import BaseSchemaGenerator


class AsyncpgSchemaGenerator(BaseSchemaGenerator):
    def _get_primary_key_create_string(self, field_name):
        return '"{}" SERIAL NOT NULL PRIMARY KEY'.format(field_name)
