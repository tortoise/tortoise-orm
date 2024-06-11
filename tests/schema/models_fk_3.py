"""
This is the testing Models — on_delete SET_NULL without null=True
"""

from tests.schema.models_cyclic import Two
from tortoise import fields
from tortoise.models import Model


class One(Model):
    tournament: fields.ForeignKeyRelation[Two] = fields.ForeignKeyField(
        "models.Two", on_delete=fields.SET_NULL
    )
