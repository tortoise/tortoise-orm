"""
Testing Models for a bad/wrong relation reference
Wrong reference. fk field parameter `to_field` with non exist field.
"""
from tortoise import fields
from tortoise.models import Model


class Tournament(Model):
    uuid = fields.UUIDField(unique=True)


class Event(Model):
    tournament = fields.ForeignKeyField(
        "models.Tournament", related_name="events", to_field="uuids"
    )
