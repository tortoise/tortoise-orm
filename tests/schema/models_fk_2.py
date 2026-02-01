"""
This is the testing Models — Bad on_delete parameter
"""

from tests.schema.models_cyclic import Two
from tortoise import fields
from tortoise.models import Model


class One(Model):
    tournament: fields.ForeignKeyRelation[Two] = fields.ForeignKeyField(
        "models.Two",
        on_delete="WABOOM",  # type:ignore
    )
