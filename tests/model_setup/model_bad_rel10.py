"""
Testing Models for a bad/wrong relation reference
Wrong reference. Two one-to-one primary keys referencing each other.
"""

from tortoise import fields
from tortoise.models import Model


class Tournament(Model):
    event: fields.OneToOneRelation["Event"] = fields.OneToOneField(
        "models.Event", primary_key=True, related_name="tournament_rel"
    )


class Event(Model):
    tournament: fields.OneToOneRelation[Tournament] = fields.OneToOneField(
        "models.Tournament", primary_key=True, related_name="event_rel"
    )
