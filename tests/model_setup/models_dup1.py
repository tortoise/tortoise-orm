"""
This is the testing Models — Duplicate 1
"""

from tortoise import fields
from tortoise.fields import CASCADE
from tortoise.models import Model


class Tournament(Model):
    id = fields.IntField(primary_key=True)


class Event(Model):
    tournament: fields.ForeignKeyRelation[Tournament] = fields.ForeignKeyField(
        "models.Tournament", related_name="events", on_delete=CASCADE
    )


class Party(Model):
    tournament: fields.ForeignKeyRelation[Tournament] = fields.ForeignKeyField(
        "models.Tournament", related_name="events", on_delete=CASCADE
    )
