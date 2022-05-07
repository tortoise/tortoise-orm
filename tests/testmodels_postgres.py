from tortoise import Model, fields
from tortoise.contrib.postgres.fields import ArrayField


class ArrayFields(Model):
    id = fields.IntField(pk=True)
    array = ArrayField()
    array_null = ArrayField(null=True)
