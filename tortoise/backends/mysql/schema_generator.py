from tortoise import fields
from tortoise.backends.base.schema_generator import BaseSchemaGenerator


class MySQLSchemaGenerator(BaseSchemaGenerator):
    def __init__(self, client, *args, **kwargs):
        super().__init__(client, *args, **kwargs)

        self.TABLE_CREATE_TEMPLATE = 'CREATE TABLE `{}` ({});'
        self.FIELD_TEMPLATE = '`{name}` {type} {nullable} {unique}'
        self.FK_TEMPLATE = ' REFERENCES `{table}` (`id`) ON DELETE {on_delete}'
        self.M2M_TABLE_TEMPLATE = (
            'CREATE TABLE `{table_name}` '
            '(`{backward_key}` INT NOT NULL REFERENCES \
              `{backward_table}` (`id`) ON DELETE CASCADE, '
            '`{forward_key}` INT NOT NULL REFERENCES `{forward_table}` (`id`) ON DELETE CASCADE);'
        )

        self.FIELD_TYPE_MAP.update({
            fields.FloatField: 'DOUBLE',
            fields.DatetimeField: 'DATETIME(6)',
            fields.TextField: 'TEXT'
        })

        self.client = client

    def _get_primary_key_create_string(self, field_name):
        return "`{}` INT UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT".format(field_name)
