"""
This example demonstrates SQL Schema generation for each DB type supported.
"""
from uuid import uuid4

from tortoise import fields
from tortoise.fields import SET_NULL
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
        "models.Tournament", related_name="events", description="FK to tournament"
    )
    participants = fields.ManyToManyField(
        "models.Team",
        related_name="events",
        through="teamevents",
        description="How participants relate",
        on_delete=SET_NULL,
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
    manager = fields.ForeignKeyField("models.Team", related_name="team_members", null=True)
    talks_to = fields.ManyToManyField("models.Team", related_name="gets_talked_to")

    class Meta:
        table_description = "The TEAMS!"
        indexes = [("manager", "key"), ["manager_id", "name"]]


class TeamAddress(Model):
    """
    The Team's address

    This is a long section of the docs that won't appear in the description.
    """

    city = fields.CharField(max_length=50, description="City")
    country = fields.CharField(max_length=50, description="Country")
    street = fields.CharField(max_length=128, description="Street Address")
    team = fields.OneToOneField(
        "models.Team", related_name="address", on_delete=fields.CASCADE, pk=True
    )


class VenueInformation(Model):
    name = fields.CharField(max_length=128)
    # This is just a comment
    #: No. of seats
    #: All this should not be part of the field description either!
    capacity = fields.IntField()
    rent = fields.FloatField()
    team = fields.OneToOneField("models.Team", on_delete=fields.SET_NULL, null=True)


class SourceFields(Model):
    id = fields.IntField(pk=True, source_field="sometable_id")
    chars = fields.CharField(max_length=255, source_field="some_chars_table", index=True)

    fk = fields.ForeignKeyField(
        "models.SourceFields", related_name="team_members", null=True, source_field="fk_sometable"
    )

    rel_to = fields.ManyToManyField(
        "models.SourceFields",
        related_name="rel_from",
        through="sometable_self",
        forward_key="sts_forward",
        backward_key="backward_sts",
    )

    class Meta:
        table = "sometable"
        indexes = [["chars"]]


class Company(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    uuid = fields.UUIDField(unique=True, default=uuid4)

    employees: fields.ReverseRelation["Employee"]


class Employee(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    company: fields.ForeignKeyRelation[Company] = fields.ForeignKeyField(
        "models.Company",
        related_name="employees",
        to_field="uuid",
    )


class DefaultPK(Model):
    val = fields.IntField()


class ZeroMixin:
    zero = fields.IntField()


class OneMixin(ZeroMixin):
    one = fields.CharField(40, null=True)


class TwoMixin:
    two = fields.CharField(40)


class AbstractModel(Model, OneMixin):
    new_field = fields.CharField(max_length=100)

    class Meta:
        abstract = True


class InheritedModel(AbstractModel, TwoMixin):
    name = fields.TextField()
