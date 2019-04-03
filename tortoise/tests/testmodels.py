"""
This is the testing Models
"""
import binascii
import os
from enum import Enum, IntEnum

from tortoise import fields
from tortoise.models import Model
from tortoise.tests.testfields import EnumField


def generate_token():
    return binascii.hexlify(os.urandom(16)).decode("ascii")


class Tournament(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    created = fields.DatetimeField(auto_now_add=True, index=True)

    def __str__(self):
        return self.name


class Reporter(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()

    class Meta:
        table = "re_port_er"

    def __str__(self):
        return self.name


class Event(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    tournament = fields.ForeignKeyField("models.Tournament", related_name="events")
    reporter = fields.ForeignKeyField("models.Reporter", null=True)
    participants = fields.ManyToManyField(
        "models.Team", related_name="events", through="event_team", backward_key="idEvent"
    )
    modified = fields.DatetimeField(auto_now=True)
    token = fields.TextField(default=generate_token)

    def __str__(self):
        return self.name


class Team(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()

    def __str__(self):
        return self.name


class EventTwo(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    tournament_id = fields.IntField()
    # Here we make link to events.Team, not models.Team
    participants = fields.ManyToManyField("events.TeamTwo")

    class Meta:
        app = "events"

    def __str__(self):
        return self.name


class TeamTwo(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()

    class Meta:
        app = "events"

    def __str__(self):
        return self.name


class IntFields(Model):
    id = fields.IntField(pk=True)
    intnum = fields.IntField()
    intnum_null = fields.IntField(null=True)


class BigIntFields(Model):
    id = fields.BigIntField(pk=True)
    intnum = fields.BigIntField()
    intnum_null = fields.BigIntField(null=True)


class SmallIntFields(Model):
    id = fields.IntField(pk=True)
    smallintnum = fields.SmallIntField()
    smallintnum_null = fields.SmallIntField(null=True)


class CharFields(Model):
    id = fields.IntField(pk=True)
    char = fields.CharField(max_length=255)
    char_null = fields.CharField(max_length=255, null=True)


class TextFields(Model):
    id = fields.IntField(pk=True)
    text = fields.TextField()
    text_null = fields.TextField(null=True)


class BooleanFields(Model):
    id = fields.IntField(pk=True)
    boolean = fields.BooleanField()
    boolean_null = fields.BooleanField(null=True)


class DecimalFields(Model):
    id = fields.IntField(pk=True)
    decimal = fields.DecimalField(max_digits=18, decimal_places=4)
    decimal_nodec = fields.DecimalField(max_digits=18, decimal_places=0)
    decimal_null = fields.DecimalField(max_digits=18, decimal_places=4, null=True)


class DatetimeFields(Model):
    id = fields.IntField(pk=True)
    datetime = fields.DatetimeField()
    datetime_null = fields.DatetimeField(null=True)
    datetime_auto = fields.DatetimeField(auto_now=True)
    datetime_add = fields.DatetimeField(auto_now_add=True)


class TimeDeltaFields(Model):
    id = fields.IntField(pk=True)
    timedelta = fields.TimeDeltaField()
    timedelta_null = fields.TimeDeltaField(null=True)


class DateFields(Model):
    id = fields.IntField(pk=True)
    date = fields.DateField()
    date_null = fields.DateField(null=True)


class FloatFields(Model):
    id = fields.IntField(pk=True)
    floatnum = fields.FloatField()
    floatnum_null = fields.FloatField(null=True)


class JSONFields(Model):
    id = fields.IntField(pk=True)
    data = fields.JSONField()
    data_null = fields.JSONField(null=True)


class UUIDFields(Model):
    id = fields.IntField(pk=True)
    data = fields.UUIDField()
    data_null = fields.UUIDField(null=True)


class MinRelation(Model):
    id = fields.IntField(pk=True)
    tournament = fields.ForeignKeyField("models.Tournament")
    participants = fields.ManyToManyField("models.Team")


class M2MOne(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255, null=True)
    two = fields.ManyToManyField("models.M2MTwo", related_name="one")


class M2MTwo(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255, null=True)


class NoID(Model):
    name = fields.CharField(max_length=255, null=True)


class RacePlacingEnum(Enum):
    FIRST = "first"
    SECOND = "second"
    THIRD = "third"
    RUNNER_UP = "runner_up"
    DNF = "dnf"


class RaceParticipant(Model):
    id = fields.IntField(pk=True)
    first_name = fields.CharField(max_length=64)
    place = EnumField(RacePlacingEnum, default=RacePlacingEnum.DNF)
    predicted_place = EnumField(RacePlacingEnum, null=True)


class UniqueTogetherFields(Model):
    id = fields.IntField(pk=True)
    first_name = fields.CharField(max_length=64)
    last_name = fields.CharField(max_length=64)

    class Meta:
        unique_together = ("first_name", "last_name")


class UniqueTogetherFieldsWithFK(Model):
    id = fields.IntField(pk=True)
    text = fields.CharField(max_length=64)
    tournament = fields.ForeignKeyField("models.Tournament")

    class Meta:
        unique_together = ("text", "tournament")


class ContactTypeEnum(IntEnum):
    work = 1
    home = 2
    other = 3


class Contact(Model):
    id = fields.IntField(pk=True)
    type = fields.IntField(default=ContactTypeEnum.other)


class ImplicitPkModel(Model):
    value = fields.TextField()


class UUIDPkModel(Model):
    id = fields.UUIDField(pk=True)


class UUIDFkRelatedModel(Model):
    model = fields.ForeignKeyField("models.UUIDPkModel", related_name="children")


class UUIDM2MRelatedModel(Model):
    value = fields.TextField(default="test")
    models = fields.ManyToManyField("models.UUIDPkModel", related_name="peers")
