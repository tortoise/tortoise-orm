"""
This example demonstrates SQL Schema generation for each DB type supported without db fk constraint.
"""

from tortoise import fields
from tortoise.models import Model


class Tournament(Model):
    tid = fields.SmallIntField(pk=True)
    name = fields.CharField(max_length=100, description="Tournament name", index=True)
    created = fields.DatetimeField(auto_now_add=True, description="Created */'`/* datetime")

    class Meta:
        table_description = "What Tournaments */'`/* we have"


class Event(Model):
    id = fields.BigIntField(pk=True, description="Event ID")
    name = fields.TextField()
    tournament = fields.ForeignKeyField(
        "models.Tournament",
        db_constraint=False,
        related_name="events",
        description="FK to tournament",
    )
    participants = fields.ManyToManyField(
        "models.Team",
        db_constraint=False,
        related_name="events",
        through="teamevents",
        description="How participants relate",
    )
    modified = fields.DatetimeField(auto_now=True)
    prize = fields.DecimalField(max_digits=10, decimal_places=2, null=True)
    token = fields.CharField(max_length=100, description="Unique token", unique=True)
    key = fields.CharField(max_length=100)

    class Meta:
        table_description = "This table contains a list of all the events"
        unique_together = [("name", "prize"), ["tournament", "key"]]


class Team(Model):
    name = fields.CharField(max_length=50, pk=True, description="The TEAM name (and PK)")
    key = fields.IntField()
    manager = fields.ForeignKeyField(
        "models.Team", db_constraint=False, related_name="team_members", null=True
    )
    talks_to = fields.ManyToManyField(
        "models.Team", db_constraint=False, related_name="gets_talked_to"
    )

    class Meta:
        table_description = "The TEAMS!"
        indexes = [("manager", "key"), ["manager_id", "name"]]
