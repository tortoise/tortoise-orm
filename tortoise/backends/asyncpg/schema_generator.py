from tortoise.backends.asyncpg.fields import JSONField
from tortoise.backends.base.schema_generator import BaseSchemaGenerator


class AsyncpgSchemaGenerator(BaseSchemaGenerator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.FIELD_TYPE_MAP.update({
            JSONField: 'jsonb'
        })

    def _get_primary_key_create_string(self, field_name):
        return '"{}" SERIAL NOT NULL PRIMARY KEY'.format(field_name)
