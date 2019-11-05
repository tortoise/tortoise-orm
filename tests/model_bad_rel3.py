"""
Testing Models for a bad/wrong relation reference
Wrong reference. App missing.
"""
from tortoise import fields
from tortoise.models import Model


class Tournament(Model):
    id = fields.IntField(pk=True)
    events: fields.RelationQueryContainer["Event"]


class Event(Model):
    tournament: fields.ForeignKey["Tournament"] = fields.ForeignKeyField(
        "Tournament", related_name="events"
    )
