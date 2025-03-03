"""
This is the testing Models — Cyclic
"""

from tests.schema.models_cyclic import Two
from tortoise import fields
from tortoise.fields import CASCADE
from tortoise.models import Model


class One(Model):
    tournament: fields.ManyToManyRelation[Two] = fields.ManyToManyField("Two", on_delete=CASCADE)
