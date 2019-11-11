"""
This is the testing Models — Duplicate 1
"""

from tortoise import fields
from tortoise.models import Model


class Tournament(Model):
    id = fields.IntField(pk=True)


class Event(Model):
    tournament = fields.ForeignKeyField("models.Tournament", related_name="events")


class Party(Model):
    tournament = fields.ForeignKeyField("models.Tournament", related_name="events")
