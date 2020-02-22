"""
Testing Models for a bad/wrong relation reference
Wrong reference. o2o field parameter `to_field` with non unique field.
"""
from tortoise import fields
from tortoise.models import Model


class Tournament(Model):
    uuid = fields.UUIDField(unique=False)


class Event(Model):
    tournament = fields.OneToOneField("models.Tournament", related_name="events", to_field="uuid")
