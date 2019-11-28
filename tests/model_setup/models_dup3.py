"""
This is the testing Models — Duplicate 3
"""

from tortoise import fields
from tortoise.models import Model


class Tournament(Model):
    id = fields.IntField(pk=True)
    event = fields.CharField(max_length=32)


class Event(Model):
    tournament = fields.OneToOneField("models.Tournament", related_name="event")
