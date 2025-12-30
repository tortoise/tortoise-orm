"""
This is the testing Models — Cyclic
"""

from tortoise import fields
from tortoise.models import Model


class One(Model):
    tournament: fields.ForeignKeyRelation["Two"] = fields.ForeignKeyField(
        "models.Two", related_name="events", on_delete=fields.RESTRICT
    )


class Two(Model):
    tournament: fields.ForeignKeyRelation["Three"] = fields.ForeignKeyField(
        "models.Three", related_name="events", on_delete=fields.RESTRICT
    )


class Three(Model):
    tournament: fields.ForeignKeyRelation[One] = fields.ForeignKeyField(
        "models.One", related_name="events", on_delete=fields.RESTRICT
    )
