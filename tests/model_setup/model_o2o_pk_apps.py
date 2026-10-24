"""
This is the testing Models — foreign key to a one-to-one primary key of another app,
each app initialised by its own init_models() call
"""

from tortoise import fields
from tortoise.models import Model


class Tournament(Model):
    class Meta:
        app = "app1"


class Event(Model):
    tournament: fields.OneToOneRelation[Tournament] = fields.OneToOneField(
        "app1.Tournament", primary_key=True, related_name="event"
    )

    class Meta:
        app = "app1"


class Team(Model):
    event: fields.ForeignKeyRelation[Event] = fields.ForeignKeyField(
        "app1.Event", related_name="teams"
    )

    class Meta:
        app = "app2"
