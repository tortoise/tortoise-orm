"""
This is the testing Models
"""
import binascii
import os
import uuid
from enum import Enum, IntEnum

from tortoise import fields
from tortoise.models import Model
from tortoise.tests.testfields import EnumField


def generate_token():
    return binascii.hexlify(os.urandom(16)).decode("ascii")


class Tournament(Model):
    id = fields.SmallIntField(pk=True)
    name = fields.CharField(max_length=255)
    desc = fields.TextField(null=True)
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
    id = fields.BigIntField(pk=True)
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
    data_default = fields.JSONField(default={"a": 1})


class UUIDFields(Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid1)
    data = fields.UUIDField()
    data_auto = fields.UUIDField(default=uuid.uuid4)
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
    desc = fields.TextField(null=True)


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
    name = fields.CharField(max_length=50, null=True)
    model = fields.ForeignKeyField("models.UUIDPkModel", related_name="children")


class UUIDM2MRelatedModel(Model):
    value = fields.TextField(default="test")
    models = fields.ManyToManyField("models.UUIDPkModel", related_name="peers")


class CharPkModel(Model):
    id = fields.CharField(max_length=64, pk=True)


class CharFkRelatedModel(Model):
    model = fields.ForeignKeyField("models.CharPkModel", related_name="children")


class CharM2MRelatedModel(Model):
    value = fields.TextField(default="test")
    models = fields.ManyToManyField("models.CharPkModel", related_name="peers")


class TimestampMixin:
    created_at = fields.DatetimeField(null=True, auto_now_add=True)
    modified_at = fields.DatetimeField(null=True, auto_now=True)


class NameMixin:
    name = fields.CharField(40, unique=True)


class MyAbstractBaseModel(NameMixin, Model):
    id = fields.IntField(pk=True)

    class Meta:
        abstract = True


class MyDerivedModel(TimestampMixin, MyAbstractBaseModel):
    first_name = fields.CharField(20, null=True)


class CommentModel(Model):
    class Meta:
        table = "comments"
        table_description = "Test Table comment"

    id = fields.IntField(pk=True, description="Primary key \r*/'`/*\n field for the comments")
    message = fields.TextField(description="Comment messages entered in the blog post")
    rating = fields.IntField(description="Upvotes done on the comment")
    escaped_comment_field = fields.TextField(description="This column acts as it's own comment")
    multiline_comment = fields.TextField(description="Some \n comment")
    commented_by = fields.TextField()


class Employee(Model):
    name = fields.CharField(max_length=50)
    manager = fields.ForeignKeyField("models.Employee", related_name="team_members", null=True)
    talks_to = fields.ManyToManyField("models.Employee", related_name="gets_talked_to")

    def __str__(self):
        return self.name

    # async def full_hierarchy__async_for(self, level=0):
    #     """
    #     Demonstrates ``async for` to fetch relations
    #
    #     An async iterator will fetch the relationship on-demand.
    #     """
    #     text = [
    #         "{}{} (to: {}) (from: {})".format(
    #             level * "  ",
    #             self,
    #             ", ".join(sorted([str(val) async for val in self.talks_to])),
    #             ", ".join(sorted([str(val) async for val in self.gets_talked_to])),
    #         )
    #     ]
    #     async for member in self.team_members:
    #         text.append(await member.full_hierarchy__async_for(level + 1))
    #     return "\n".join(text)

    async def full_hierarchy__fetch_related(self, level=0):
        """
        Demonstrates ``await .fetch_related`` to fetch relations

        On prefetching the data, the relationship files will contain a regular list.

        This is how one would get relations working on sync serialisation/templating frameworks.
        """
        await self.fetch_related("team_members", "talks_to", "gets_talked_to")
        text = [
            "{}{} (to: {}) (from: {})".format(
                level * "  ",
                self,
                ", ".join(sorted([str(val) for val in self.talks_to])),
                ", ".join(sorted([str(val) for val in self.gets_talked_to])),
            )
        ]
        for member in self.team_members:
            text.append(await member.full_hierarchy__fetch_related(level + 1))
        return "\n".join(text)


class StraightFields(Model):
    id = fields.IntField(pk=True, description="Da PK")
    chars = fields.CharField(max_length=255, index=True, description="Some chars")
    blip = fields.CharField(max_length=255, default="BLIP")
    fk = fields.ForeignKeyField(
        "models.StraightFields", related_name="fkrev", null=True, description="Tree!"
    )
    rel_to = fields.ManyToManyField(
        "models.StraightFields", related_name="rel_from", description="M2M to myself"
    )

    class Meta:
        unique_together = [["chars", "blip"]]
        table_description = "Straight auto-mapped fields"


class SourceFields(Model):
    id = fields.IntField(pk=True, source_field="sometable_id", description="Da PK")
    chars = fields.CharField(
        max_length=255, source_field="some_chars_table", index=True, description="Some chars"
    )
    blip = fields.CharField(max_length=255, default="BLIP", source_field="da_blip")
    fk = fields.ForeignKeyField(
        "models.SourceFields",
        related_name="fkrev",
        null=True,
        source_field="fk_sometable",
        description="Tree!",
    )
    rel_to = fields.ManyToManyField(
        "models.SourceFields",
        related_name="rel_from",
        through="sometable_self",
        forward_key="sts_forward",
        backward_key="backward_sts",
        description="M2M to myself",
    )

    class Meta:
        table = "sometable"
        unique_together = [["chars", "blip"]]
        table_description = "Source mapped fields"
