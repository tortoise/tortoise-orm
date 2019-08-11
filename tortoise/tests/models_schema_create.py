"""
This example demonstrates SQL Schema generation for each DB type supported.
"""
from tortoise import fields
from tortoise.models import Model


class Tournament(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField(description="Tournament name", index=True)
    created = fields.DatetimeField(auto_now_add=True, description="Created */'`/* datetime")

    class Meta:
        table_description = "What Tournaments */'`/* we have"


class Event(Model):
    id = fields.IntField(pk=True, description="Event ID")
    name = fields.TextField(unique=True)
    tournament = fields.ForeignKeyField(
        "models.Tournament", related_name="events", description="FK to tournament"
    )
    participants = fields.ManyToManyField(
        "models.Team",
        related_name="events",
        through="event_team",
        description="How participants relate",
    )
    modified = fields.DatetimeField(auto_now=True)
    prize = fields.DecimalField(max_digits=10, decimal_places=2, null=True)
    token = fields.CharField(max_length=100, description="Unique token", unique=True)

    class Meta:
        table_description = "This table contains a list of all the events"


class Team(Model):
    name = fields.CharField(max_length=50, pk=True, description="The TEAM name (and PK)")

    class Meta:
        table_description = "The TEAMS!"
