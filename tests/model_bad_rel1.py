"""
Testing Models for a bad/wrong relation reference
"""
from tortoise import fields
from tortoise.models import Model


class Tournament(Model):
    id = fields.IntField(pk=True)
    events: fields.RelationQueryContainer["Event"]


class Event(Model):
    tournament: fields.ForeignKey[Tournament] = fields.ForeignKeyField(
        "app.Tournament", related_name="events"
    )
