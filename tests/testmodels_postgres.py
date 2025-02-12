from tortoise import Model, fields
from tortoise.contrib.postgres.fields import ArrayField


class ArrayFields(Model):
    id = fields.IntField(primary_key=True)
    array = ArrayField()
    array_null = ArrayField(null=True)
    array_str = ArrayField(element_type="varchar(1)", null=True)
    array_smallint = ArrayField(element_type="smallint", null=True)
