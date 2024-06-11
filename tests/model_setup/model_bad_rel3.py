"""
Testing Models for a bad/wrong relation reference
Wrong reference. App missing.
"""

from tortoise import fields
from tortoise.models import Model


class Tournament(Model):
    id = fields.IntField(primary_key=True)


class Event(Model):
    tournament: fields.ForeignKeyRelation[Tournament] = fields.ForeignKeyField(
        "Tournament", related_name="events"
    )
