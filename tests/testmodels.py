"""
This is the testing Models
"""
import binascii
import os
import uuid
from enum import Enum, IntEnum

from tortoise import fields
from tortoise.models import Model


def generate_token():
    return binascii.hexlify(os.urandom(16)).decode("ascii")


class Tournament(Model):
    id = fields.SmallIntField(pk=True)
    name = fields.CharField(max_length=255)
    desc = fields.TextField(null=True)
    created = fields.DatetimeField(auto_now_add=True, index=True)

    events: fields.ReverseRelation["Event"]
    minrelations: fields.ReverseRelation["MinRelation"]
    uniquetogetherfieldswithfks: fields.ReverseRelation["UniqueTogetherFieldsWithFK"]

    def __str__(self):
        return self.name


class Reporter(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()

    events: fields.ReverseRelation["Event"]

    class Meta:
        table = "re_port_er"

    def __str__(self):
        return self.name


class Event(Model):
    id = fields.BigIntField(pk=True)
    name = fields.TextField()
    tournament: fields.ForeignKeyRelation["Tournament"] = fields.ForeignKeyField(
        "models.Tournament", related_name="events"
    )
    reporter: fields.ForeignKeyNullableRelation[Reporter] = fields.ForeignKeyField(
        "models.Reporter", null=True
    )
    participants: fields.ManyToManyRelation["Team"] = fields.ManyToManyField(
        "models.Team", related_name="events", through="event_team", backward_key="idEvent"
    )
    modified = fields.DatetimeField(auto_now=True)
    token = fields.TextField(default=generate_token)
    alias = fields.IntField(null=True)

    def __str__(self):
        return self.name


class Address(Model):
    city = fields.CharField(max_length=64)
    street = fields.CharField(max_length=128)

    event: fields.OneToOneRelation[Event] = fields.OneToOneField(
        "models.Event", on_delete=fields.CASCADE, related_name="address", null=True
    )


class Team(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()

    events: fields.ManyToManyRelation[Event]
    minrelation_through: fields.ManyToManyRelation["MinRelation"]
    alias = fields.IntField(null=True)

    def __str__(self):
        return self.name


class EventTwo(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    tournament_id = fields.IntField()
    # Here we make link to events.Team, not models.Team
    participants: fields.ManyToManyRelation["TeamTwo"] = fields.ManyToManyField("events.TeamTwo")

    class Meta:
        app = "events"

    def __str__(self):
        return self.name


class TeamTwo(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()

    eventtwo_through: fields.ManyToManyRelation[EventTwo]

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


class BinaryFields(Model):
    id = fields.IntField(pk=True)
    binary = fields.BinaryField()
    binary_null = fields.BinaryField(null=True)


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
    tournament: fields.ForeignKeyRelation[Tournament] = fields.ForeignKeyField("models.Tournament")
    participants: fields.ManyToManyRelation[Team] = fields.ManyToManyField("models.Team")


class M2MOne(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255, null=True)
    two: fields.ManyToManyRelation["M2MTwo"] = fields.ManyToManyField(
        "models.M2MTwo", related_name="one"
    )


class M2MTwo(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255, null=True)

    one: fields.ManyToManyRelation[M2MOne]


class NoID(Model):
    name = fields.CharField(max_length=255, null=True)
    desc = fields.TextField(null=True)


class UniqueName(Model):
    name = fields.CharField(max_length=20, null=True, unique=True)


class UniqueTogetherFields(Model):
    id = fields.IntField(pk=True)
    first_name = fields.CharField(max_length=64)
    last_name = fields.CharField(max_length=64)

    class Meta:
        unique_together = ("first_name", "last_name")


class UniqueTogetherFieldsWithFK(Model):
    id = fields.IntField(pk=True)
    text = fields.CharField(max_length=64)
    tournament: fields.ForeignKeyRelation[Tournament] = fields.ForeignKeyField("models.Tournament")

    class Meta:
        unique_together = ("text", "tournament")


class ImplicitPkModel(Model):
    value = fields.TextField()


class UUIDPkModel(Model):
    id = fields.UUIDField(pk=True)

    children: fields.ReverseRelation["UUIDFkRelatedModel"]
    children_null: fields.ReverseRelation["UUIDFkRelatedNullModel"]
    peers: fields.ManyToManyRelation["UUIDM2MRelatedModel"]


class UUIDFkRelatedModel(Model):
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=50, null=True)
    model: fields.ForeignKeyRelation[UUIDPkModel] = fields.ForeignKeyField(
        "models.UUIDPkModel", related_name="children"
    )


class UUIDFkRelatedNullModel(Model):
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=50, null=True)
    model: fields.ForeignKeyNullableRelation[UUIDPkModel] = fields.ForeignKeyField(
        "models.UUIDPkModel", related_name=False, null=True
    )
    parent: fields.OneToOneNullableRelation[UUIDPkModel] = fields.OneToOneField(
        "models.UUIDPkModel", related_name=False, null=True
    )


class UUIDM2MRelatedModel(Model):
    id = fields.UUIDField(pk=True)
    value = fields.TextField(default="test")
    models: fields.ManyToManyRelation[UUIDPkModel] = fields.ManyToManyField(
        "models.UUIDPkModel", related_name="peers"
    )


class UUIDPkSourceModel(Model):
    id = fields.UUIDField(pk=True, source_field="a")

    class Meta:
        table = "upsm"


class UUIDFkRelatedSourceModel(Model):
    id = fields.UUIDField(pk=True, source_field="b")
    name = fields.CharField(max_length=50, null=True, source_field="c")
    model = fields.ForeignKeyField(
        "models.UUIDPkSourceModel", related_name="children", source_field="d"
    )

    class Meta:
        table = "ufrsm"


class UUIDFkRelatedNullSourceModel(Model):
    id = fields.UUIDField(pk=True, source_field="i")
    name = fields.CharField(max_length=50, null=True, source_field="j")
    model = fields.ForeignKeyField(
        "models.UUIDPkSourceModel", related_name="children_null", source_field="k", null=True
    )

    class Meta:
        table = "ufrnsm"


class UUIDM2MRelatedSourceModel(Model):
    id = fields.UUIDField(pk=True, source_field="e")
    value = fields.TextField(default="test", source_field="f")
    models = fields.ManyToManyField(
        "models.UUIDPkSourceModel", related_name="peers", forward_key="e", backward_key="h"
    )

    class Meta:
        table = "umrsm"


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

    manager: fields.ForeignKeyNullableRelation["Employee"] = fields.ForeignKeyField(
        "models.Employee", related_name="team_members", null=True
    )
    team_members: fields.ReverseRelation["Employee"]

    talks_to: fields.ManyToManyRelation["Employee"] = fields.ManyToManyField(
        "models.Employee", related_name="gets_talked_to"
    )
    gets_talked_to: fields.ManyToManyRelation["Employee"]

    def __str__(self):
        return self.name

    async def full_hierarchy__async_for(self, level=0):
        """
        Demonstrates ``async for` to fetch relations

        An async iterator will fetch the relationship on-demand.
        """
        text = [
            "{}{} (to: {}) (from: {})".format(
                level * "  ",
                self,
                ", ".join(sorted([str(val) async for val in self.talks_to])),
                ", ".join(sorted([str(val) async for val in self.gets_talked_to])),
            )
        ]
        async for member in self.team_members:
            text.append(await member.full_hierarchy__async_for(level + 1))
        return "\n".join(text)

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
    eyedee = fields.IntField(pk=True, description="Da PK")
    chars = fields.CharField(max_length=50, index=True, description="Some chars")
    blip = fields.CharField(max_length=50, default="BLIP")

    fk: fields.ForeignKeyNullableRelation["StraightFields"] = fields.ForeignKeyField(
        "models.StraightFields", related_name="fkrev", null=True, description="Tree!"
    )
    fkrev: fields.ReverseRelation["StraightFields"]

    o2o: fields.OneToOneNullableRelation["StraightFields"] = fields.OneToOneField(
        "models.StraightFields", related_name="o2o_rev", null=True, description="Line"
    )
    o2o_rev: fields.Field

    rel_to: fields.ManyToManyRelation["StraightFields"] = fields.ManyToManyField(
        "models.StraightFields", related_name="rel_from", description="M2M to myself"
    )
    rel_from: fields.ManyToManyRelation["StraightFields"]

    class Meta:
        unique_together = [["chars", "blip"]]
        table_description = "Straight auto-mapped fields"


class SourceFields(Model):
    eyedee = fields.IntField(pk=True, source_field="sometable_id", description="Da PK")
    chars = fields.CharField(
        max_length=50, source_field="some_chars_table", index=True, description="Some chars"
    )
    blip = fields.CharField(max_length=50, default="BLIP", source_field="da_blip")

    fk: fields.ForeignKeyNullableRelation["SourceFields"] = fields.ForeignKeyField(
        "models.SourceFields",
        related_name="fkrev",
        null=True,
        source_field="fk_sometable",
        description="Tree!",
    )
    fkrev: fields.ReverseRelation["SourceFields"]

    o2o: fields.OneToOneNullableRelation["SourceFields"] = fields.OneToOneField(
        "models.SourceFields",
        related_name="o2o_rev",
        null=True,
        source_field="o2o_sometable",
        description="Line",
    )
    o2o_rev: fields.Field

    rel_to: fields.ManyToManyRelation["SourceFields"] = fields.ManyToManyField(
        "models.SourceFields",
        related_name="rel_from",
        through="sometable_self",
        forward_key="sts_forward",
        backward_key="backward_sts",
        description="M2M to myself",
    )
    rel_from: fields.ManyToManyRelation["SourceFields"]

    class Meta:
        table = "sometable"
        unique_together = [["chars", "blip"]]
        table_description = "Source mapped fields"


class Service(IntEnum):
    python_programming = 1
    database_design = 2
    system_administration = 3


class Currency(str, Enum):
    HUF = "HUF"
    EUR = "EUR"
    USD = "USD"


class EnumFields(Model):
    service: Service = fields.IntEnumField(Service)
    currency: Currency = fields.CharEnumField(Currency, default=Currency.HUF)


class DoubleFK(Model):
    name = fields.CharField(max_length=50)
    left = fields.ForeignKeyField("models.DoubleFK", null=True, related_name="left_rel")
    right = fields.ForeignKeyField("models.DoubleFK", null=True, related_name="right_rel")
