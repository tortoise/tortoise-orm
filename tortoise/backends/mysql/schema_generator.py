from tortoise import fields
from tortoise.backends.base.schema_generator import BaseSchemaGenerator


class MySQLSchemaGenerator(BaseSchemaGenerator):
    def __init__(self, client, *args, **kwargs):
        super().__init__(client, *args, **kwargs)

        self.FIELD_TYPE_MAP.update({
                fields.FloatField: 'DOUBLE',
                fields.JSONField: 'JSON',
            })
        self.client = client

    def _get_primary_key_create_string(self, field_name):
        return "{} INT UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT".replace('{}', field_name)

