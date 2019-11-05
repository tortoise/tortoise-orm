"""
This is the testing Models — Cyclic
"""
from tortoise import fields
from tortoise.models import Model


class One(Model):
    tournament: fields.ForeignKey["Two"] = fields.ForeignKeyField(
        "models.Two", related_name="events"
    )
    events: fields.RelationQueryContainer["Three"]


class Two(Model):
    tournament: fields.ForeignKey["Three"] = fields.ForeignKeyField(
        "models.Three", related_name="events"
    )
    events: fields.RelationQueryContainer[One]


class Three(Model):
    tournament: fields.ForeignKey[One] = fields.ForeignKeyField("models.One", related_name="events")
    events: fields.RelationQueryContainer[Two]
