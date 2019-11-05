"""
This is the testing Models — Duplicate 1
"""
from typing import Union

from tortoise import fields
from tortoise.models import Model


class Tournament(Model):
    id = fields.IntField(pk=True)
    events: fields.RelationQueryContainer[Union["Event", "Party"]]


class Event(Model):
    tournament: fields.ForeignKey[Tournament] = fields.ForeignKeyField(
        "models.Tournament", related_name="events"
    )


class Party(Model):
    tournament: fields.ForeignKey[Tournament] = fields.ForeignKeyField(
        "models.Tournament", related_name="events"
    )
