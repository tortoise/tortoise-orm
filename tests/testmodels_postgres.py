from tortoise import Model, fields
from tortoise.contrib.postgres.fields import ArrayField


class ArrayFields(Model):
    id = fields.IntField(primary_key=True)
    array = ArrayField()
    array_null = ArrayField(null=True)
