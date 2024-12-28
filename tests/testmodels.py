"""
This is the testing Models
"""

import binascii
import datetime
import os
import re
import uuid
from decimal import Decimal
from enum import Enum, IntEnum
from typing import List, Union

import pytz
from pydantic import BaseModel, ConfigDict

from tortoise import fields
from tortoise.exceptions import ValidationError
from tortoise.fields import NO_ACTION
from tortoise.manager import Manager
from tortoise.models import Model
from tortoise.queryset import QuerySet
from tortoise.validators import (
    CommaSeparatedIntegerListValidator,
    MaxValueValidator,
    MinValueValidator,
    RegexValidator,
    validate_ipv4_address,
    validate_ipv6_address,
)


def generate_token():
    return binascii.hexlify(os.urandom(16)).decode("ascii")


class TestSchemaForJSONField(BaseModel):
    foo: int
    bar: str
    __test__ = False


json_pydantic_default = TestSchemaForJSONField(foo=1, bar="baz")


class Author(Model):
    name = fields.CharField(max_length=255)


class Book(Model):
    name = fields.CharField(max_length=255)
    author: fields.ForeignKeyRelation[Author] = fields.ForeignKeyField(
        "models.Author", related_name="books"
    )
    rating = fields.FloatField()
    subject = fields.CharField(max_length=255, null=True)


class BookNoConstraint(Model):
    name = fields.CharField(max_length=255)
    author: fields.ForeignKeyRelation[Author] = fields.ForeignKeyField(
        "models.Author", db_constraint=False
    )
    rating = fields.FloatField()


class Tournament(Model):
    id = fields.SmallIntField(primary_key=True)
    name = fields.CharField(max_length=255)
    desc = fields.TextField(null=True)
    created = fields.DatetimeField(auto_now_add=True, db_index=True)

    events: fields.ReverseRelation["Event"]
    minrelations: fields.ReverseRelation["MinRelation"]
    uniquetogetherfieldswithfks: fields.ReverseRelation["UniqueTogetherFieldsWithFK"]

    class PydanticMeta:
        exclude = ("minrelations", "uniquetogetherfieldswithfks")

    def __str__(self):
        return self.name


class Reporter(Model):
    """Whom is assigned as the reporter"""

    id = fields.IntField(primary_key=True)
    name = fields.TextField()

    events: fields.ReverseRelation["Event"]

    class Meta:
        table = "re_port_er"

    def __str__(self):
        return self.name


class Event(Model):
    """Events on the calendar"""

    event_id = fields.BigIntField(primary_key=True)
    #: The name
    name = fields.TextField()
    #: What tournaments is a happenin'
    tournament: fields.ForeignKeyRelation["Tournament"] = fields.ForeignKeyField(
        "models.Tournament", related_name="events"
    )
    reporter: fields.ForeignKeyNullableRelation[Reporter] = fields.ForeignKeyField(
        "models.Reporter", null=True
    )
    participants: fields.ManyToManyRelation["Team"] = fields.ManyToManyField(
        "models.Team",
        related_name="events",
        through="event_team",
        backward_key="idEvent",
    )
    modified = fields.DatetimeField(auto_now=True)
    token = fields.TextField(default=generate_token)
    alias = fields.IntField(null=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ModelTestPydanticMetaBackwardRelations1(Model):
    class PydanticMeta:
        backward_relations = False


class ModelTestPydanticMetaBackwardRelations2(Model): ...


class ModelTestPydanticMetaBackwardRelations3(Model):
    one: fields.ForeignKeyRelation[ModelTestPydanticMetaBackwardRelations1] = (
        fields.ForeignKeyField(
            "models.ModelTestPydanticMetaBackwardRelations1", related_name="threes"
        )
    )
    two: fields.ForeignKeyRelation[ModelTestPydanticMetaBackwardRelations2] = (
        fields.ForeignKeyField(
            "models.ModelTestPydanticMetaBackwardRelations2", related_name="threes"
        )
    )


class Node(Model):
    name = fields.CharField(max_length=10)


class Tree(Model):
    parent: fields.ForeignKeyRelation[Node] = fields.ForeignKeyField(
        "models.Node", related_name="parent_trees"
    )
    child: fields.ForeignKeyRelation[Node] = fields.ForeignKeyField(
        "models.Node", related_name="children_trees", on_delete=NO_ACTION
    )


class Address(Model):
    city = fields.CharField(max_length=64)
    street = fields.CharField(max_length=128)

    event: fields.OneToOneRelation[Event] = fields.OneToOneField(
        "models.Event",
        on_delete=fields.CASCADE,
        related_name="address",
        primary_key=True,
    )


class M2mWithO2oPk(Model):
    name = fields.CharField(max_length=64)
    address: fields.ManyToManyRelation["Address"] = fields.ManyToManyField("models.Address")


class O2oPkModelWithM2m(Model):
    author: fields.OneToOneRelation[Author] = fields.OneToOneField(
        "models.Author",
        on_delete=fields.CASCADE,
        primary_key=True,
    )
    nodes: fields.ManyToManyRelation["Node"] = fields.ManyToManyField("models.Node")


class Dest_null(Model):
    name = fields.CharField(max_length=64)


class O2O_null(Model):
    name = fields.CharField(max_length=64)
    event: fields.OneToOneNullableRelation[Event] = fields.OneToOneField(
        "models.Dest_null",
        on_delete=fields.CASCADE,
        related_name="address_null",
        null=True,
    )


class Team(Model):
    """
    Team that is a playing
    """

    id = fields.IntField(primary_key=True)
    name = fields.TextField()

    events: fields.ManyToManyRelation[Event]
    minrelation_through: fields.ManyToManyRelation["MinRelation"]
    alias = fields.IntField(null=True)

    class Meta:
        ordering = ["id"]

    class PydanticMeta:
        exclude = ("minrelations",)

    def __str__(self):
        return self.name


class EventTwo(Model):
    id = fields.IntField(primary_key=True)
    name = fields.TextField()
    tournament_id = fields.IntField()
    # Here we make link to events.Team, not models.Team
    participants: fields.ManyToManyRelation["TeamTwo"] = fields.ManyToManyField("events.TeamTwo")

    class Meta:
        app = "events"

    def __str__(self):
        return self.name


class TeamTwo(Model):
    id = fields.IntField(primary_key=True)
    name = fields.TextField()

    eventtwo_through: fields.ManyToManyRelation[EventTwo]

    class Meta:
        app = "events"

    def __str__(self):
        return self.name


class IntFields(Model):
    id = fields.IntField(primary_key=True)
    intnum = fields.IntField()
    intnum_null = fields.IntField(null=True)


class BigIntFields(Model):
    id = fields.BigIntField(primary_key=True)
    intnum = fields.BigIntField()
    intnum_null = fields.BigIntField(null=True)


class SmallIntFields(Model):
    id = fields.IntField(primary_key=True)
    smallintnum = fields.SmallIntField()
    smallintnum_null = fields.SmallIntField(null=True)


class CharFields(Model):
    id = fields.IntField(primary_key=True)
    char = fields.CharField(max_length=255)
    char_null = fields.CharField(max_length=255, null=True)


class TextFields(Model):
    id = fields.IntField(primary_key=True)
    text = fields.TextField()
    text_null = fields.TextField(null=True)


class BooleanFields(Model):
    id = fields.IntField(primary_key=True)
    boolean = fields.BooleanField()
    boolean_null = fields.BooleanField(null=True)


class BinaryFields(Model):
    id = fields.IntField(primary_key=True)
    binary = fields.BinaryField()
    binary_null = fields.BinaryField(null=True)


class DecimalFields(Model):
    id = fields.IntField(primary_key=True)
    decimal = fields.DecimalField(max_digits=18, decimal_places=4)
    decimal_nodec = fields.DecimalField(max_digits=18, decimal_places=0)
    decimal_null = fields.DecimalField(max_digits=18, decimal_places=4, null=True)


class DatetimeFields(Model):
    id = fields.IntField(primary_key=True)
    datetime = fields.DatetimeField()
    datetime_null = fields.DatetimeField(null=True)
    datetime_auto = fields.DatetimeField(auto_now=True)
    datetime_add = fields.DatetimeField(auto_now_add=True)


class TimeDeltaFields(Model):
    id = fields.IntField(primary_key=True)
    timedelta = fields.TimeDeltaField()
    timedelta_null = fields.TimeDeltaField(null=True)


class DateFields(Model):
    id = fields.IntField(primary_key=True)
    date = fields.DateField()
    date_null = fields.DateField(null=True)


class TimeFields(Model):
    id = fields.IntField(primary_key=True)
    time = fields.TimeField()
    time_null = fields.TimeField(null=True)


class FloatFields(Model):
    id = fields.IntField(primary_key=True)
    floatnum = fields.FloatField()
    floatnum_null = fields.FloatField(null=True)


def raise_if_not_dict_or_list(value: Union[dict, list]):
    if not isinstance(value, (dict, list)):
        raise ValidationError("Value must be a dict or list.")


class JSONFields(Model):
    """
    This model contains many JSON blobs
    """

    id = fields.IntField(primary_key=True)
    data = fields.JSONField()  # type: ignore # Test cases where generics are not provided
    data_null = fields.JSONField[Union[dict, list]](null=True)
    data_default = fields.JSONField[dict](default={"a": 1})

    # From Python 3.10 onwards, validator can be defined with staticmethod
    data_validate = fields.JSONField[Union[dict, list]](
        null=True, validators=[raise_if_not_dict_or_list]
    )

    # Test cases where generics are provided and the type is a pydantic base model
    data_pydantic = fields.JSONField[TestSchemaForJSONField](
        default=json_pydantic_default, field_type=TestSchemaForJSONField
    )


class UUIDFields(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid1)
    data = fields.UUIDField()
    data_auto = fields.UUIDField(default=uuid.uuid4)
    data_null = fields.UUIDField(null=True)


class MinRelation(Model):
    id = fields.IntField(primary_key=True)
    tournament: fields.ForeignKeyRelation[Tournament] = fields.ForeignKeyField("models.Tournament")
    participants: fields.ManyToManyRelation[Team] = fields.ManyToManyField("models.Team")


class M2MOne(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=255, null=True)
    two: fields.ManyToManyRelation["M2MTwo"] = fields.ManyToManyField(
        "models.M2MTwo", related_name="one"
    )


class M2MTwo(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=255, null=True)

    one: fields.ManyToManyRelation[M2MOne]


class NoID(Model):
    name = fields.CharField(max_length=255, null=True)
    desc = fields.TextField(null=True)


class UniqueName(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=20, null=True, unique=True)
    optional = fields.CharField(max_length=20, null=True)
    other_optional = fields.CharField(max_length=20, null=True)


class UniqueTogetherFields(Model):
    id = fields.IntField(primary_key=True)
    first_name = fields.CharField(max_length=64)
    last_name = fields.CharField(max_length=64)

    class Meta:
        unique_together = ("first_name", "last_name")


class UniqueTogetherFieldsWithFK(Model):
    id = fields.IntField(primary_key=True)
    text = fields.CharField(max_length=64)
    tournament: fields.ForeignKeyRelation[Tournament] = fields.ForeignKeyField("models.Tournament")

    class Meta:
        unique_together = ("text", "tournament")


class ImplicitPkModel(Model):
    value = fields.TextField()


class UUIDPkModel(Model):
    id = fields.UUIDField(primary_key=True)

    children: fields.ReverseRelation["UUIDFkRelatedModel"]
    children_null: fields.ReverseRelation["UUIDFkRelatedNullModel"]
    peers: fields.ManyToManyRelation["UUIDM2MRelatedModel"]


class UUIDFkRelatedModel(Model):
    id = fields.UUIDField(primary_key=True)
    name = fields.CharField(max_length=50, null=True)
    model: fields.ForeignKeyRelation[UUIDPkModel] = fields.ForeignKeyField(
        "models.UUIDPkModel", related_name="children"
    )


class UUIDFkRelatedNullModel(Model):
    id = fields.UUIDField(primary_key=True)
    name = fields.CharField(max_length=50, null=True)
    model: fields.ForeignKeyNullableRelation[UUIDPkModel] = fields.ForeignKeyField(
        "models.UUIDPkModel", related_name=False, null=True
    )
    parent: fields.OneToOneNullableRelation[UUIDPkModel] = fields.OneToOneField(
        "models.UUIDPkModel", related_name=False, null=True, on_delete=NO_ACTION
    )


class UUIDM2MRelatedModel(Model):
    id = fields.UUIDField(primary_key=True)
    value = fields.TextField(default="test")
    models: fields.ManyToManyRelation[UUIDPkModel] = fields.ManyToManyField(
        "models.UUIDPkModel", related_name="peers"
    )


class UUIDPkSourceModel(Model):
    id = fields.UUIDField(primary_key=True, source_field="a")

    class Meta:
        table = "upsm"


class UUIDFkRelatedSourceModel(Model):
    id = fields.UUIDField(primary_key=True, source_field="b")
    name = fields.CharField(max_length=50, null=True, source_field="c")
    model: fields.ForeignKeyRelation[UUIDPkSourceModel] = fields.ForeignKeyField(
        "models.UUIDPkSourceModel", related_name="children", source_field="d"
    )

    class Meta:
        table = "ufrsm"


class UUIDFkRelatedNullSourceModel(Model):
    id = fields.UUIDField(primary_key=True, source_field="i")
    name = fields.CharField(max_length=50, null=True, source_field="j")
    model: fields.ForeignKeyNullableRelation[UUIDPkSourceModel] = fields.ForeignKeyField(
        "models.UUIDPkSourceModel",
        related_name="children_null",
        source_field="k",
        null=True,
    )

    class Meta:
        table = "ufrnsm"


class UUIDM2MRelatedSourceModel(Model):
    id = fields.UUIDField(primary_key=True, source_field="e")
    value = fields.TextField(default="test", source_field="f")
    models: fields.ManyToManyRelation[UUIDPkSourceModel] = fields.ManyToManyField(
        "models.UUIDPkSourceModel",
        related_name="peers",
        forward_key="e",
        backward_key="h",
    )

    class Meta:
        table = "umrsm"


class CharPkModel(Model):
    id = fields.CharField(max_length=64, primary_key=True)


class CharFkRelatedModel(Model):
    model: fields.ForeignKeyRelation[CharPkModel] = fields.ForeignKeyField(
        "models.CharPkModel", related_name="children"
    )


class CharM2MRelatedModel(Model):
    value = fields.TextField(default="test")
    models: fields.ManyToManyRelation[CharPkModel] = fields.ManyToManyField(
        "models.CharPkModel", related_name="peers"
    )


class TimestampMixin:
    created_at = fields.DatetimeField(null=True, auto_now_add=True)
    modified_at = fields.DatetimeField(null=True, auto_now=True)


class NameMixin:
    name = fields.CharField(40, unique=True)


class MyAbstractBaseModel(NameMixin, Model):
    id = fields.IntField(primary_key=True)

    class Meta:
        abstract = True


class MyDerivedModel(TimestampMixin, MyAbstractBaseModel):
    first_name = fields.CharField(20, null=True)


class CommentModel(Model):
    class Meta:
        table = "comments"
        table_description = "Test Table comment"

    id = fields.IntField(
        primary_key=True, description="Primary key \r*/'`/*\n field for the comments"
    )
    message = fields.TextField(description="Comment messages entered in the blog post")
    rating = fields.IntField(description="Upvotes done on the comment")
    escaped_comment_field = fields.TextField(description="This column acts as it's own comment")
    multiline_comment = fields.TextField(description="Some \n comment")
    commented_by = fields.TextField()


class Employee(Model):
    name = fields.CharField(max_length=50)

    manager: fields.ForeignKeyNullableRelation["Employee"] = fields.ForeignKeyField(
        "models.Employee", related_name="team_members", null=True, on_delete=NO_ACTION
    )
    team_members: fields.ReverseRelation["Employee"]

    talks_to: fields.ManyToManyRelation["Employee"] = fields.ManyToManyField(
        "models.Employee", related_name="gets_talked_to", on_delete=NO_ACTION
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
                ", ".join(sorted(str(val) for val in self.talks_to)),
                ", ".join(sorted(str(val) for val in self.gets_talked_to)),
            )
        ]
        for member in self.team_members:
            text.append(await member.full_hierarchy__fetch_related(level + 1))
        return "\n".join(text)

    def name_length(self) -> int:
        # Computes length of name
        # Note that this function needs to be annotated with a return type so that pydantic
        # can generate a valid schema
        return len(self.name)

    def team_size(self) -> int:
        """
        Computes team size.

        Note that this function needs to be annotated with a return type so that pydantic can
         generate a valid schema.

        Note that the pydantic serializer can't call async methods, but the tortoise helpers
         pre-fetch relational data, so that it is available before serialization. So we don't
         need to await the relation. We do however have to protect against the case where no
         prefetching was done, hence catching and handling the
         ``tortoise.exceptions.NoValuesFetched`` exception.
        """
        try:
            return len(self.team_members)
        except AttributeError:
            return 0

    def not_annotated(self):
        raise NotImplementedError("Not Done")

    class Meta:
        ordering = ["id"]

    class PydanticMeta:
        computed = ["name_length", "team_size", "not_annotated"]
        exclude = ["manager", "gets_talked_to"]
        allow_cycles = True
        max_recursion = 2


class StraightFields(Model):
    eyedee = fields.IntField(primary_key=True, description="Da PK")
    chars = fields.CharField(max_length=50, db_index=True, description="Some chars")
    blip = fields.CharField(max_length=50, default="BLIP")
    nullable = fields.CharField(max_length=50, null=True)

    fk: fields.ForeignKeyNullableRelation["StraightFields"] = fields.ForeignKeyField(
        "models.StraightFields",
        related_name="fkrev",
        null=True,
        description="Tree!",
        on_delete=NO_ACTION,
    )
    fkrev: fields.ReverseRelation["StraightFields"]

    o2o: fields.OneToOneNullableRelation["StraightFields"] = fields.OneToOneField(
        "models.StraightFields",
        related_name="o2o_rev",
        null=True,
        description="Line",
        on_delete=NO_ACTION,
    )
    o2o_rev: fields.Field

    rel_to: fields.ManyToManyRelation["StraightFields"] = fields.ManyToManyField(
        "models.StraightFields",
        related_name="rel_from",
        description="M2M to myself",
        on_delete=fields.NO_ACTION,
    )
    rel_from: fields.ManyToManyRelation["StraightFields"]

    class Meta:
        unique_together = [["chars", "blip"]]
        table_description = "Straight auto-mapped fields"


class SourceFields(Model):
    """
    A Docstring.
    """

    eyedee = fields.IntField(primary_key=True, source_field="sometable_id", description="Da PK")
    # A regular comment
    chars = fields.CharField(
        max_length=50,
        source_field="some_chars_table",
        db_index=True,
        description="Some chars",
    )
    #: A docstring comment
    blip = fields.CharField(max_length=50, default="BLIP", source_field="da_blip")
    nullable = fields.CharField(max_length=50, null=True, source_field="some_nullable")

    fk: fields.ForeignKeyNullableRelation["SourceFields"] = fields.ForeignKeyField(
        "models.SourceFields",
        related_name="fkrev",
        null=True,
        source_field="fk_sometable",
        description="Tree!",
        on_delete=NO_ACTION,
    )
    fkrev: fields.ReverseRelation["SourceFields"]

    o2o: fields.OneToOneNullableRelation["SourceFields"] = fields.OneToOneField(
        "models.SourceFields",
        related_name="o2o_rev",
        null=True,
        source_field="o2o_sometable",
        description="Line",
        on_delete=NO_ACTION,
    )
    o2o_rev: fields.Field

    rel_to: fields.ManyToManyRelation["SourceFields"] = fields.ManyToManyField(
        "models.SourceFields",
        related_name="rel_from",
        through="sometable_self",
        forward_key="sts_forward",
        backward_key="backward_sts",
        description="M2M to myself",
        on_delete=fields.NO_ACTION,
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
    left: fields.ForeignKeyNullableRelation["DoubleFK"] = fields.ForeignKeyField(
        "models.DoubleFK", null=True, related_name="left_rel", on_delete=NO_ACTION
    )
    right: fields.ForeignKeyNullableRelation["DoubleFK"] = fields.ForeignKeyField(
        "models.DoubleFK", null=True, related_name="right_rel", on_delete=NO_ACTION
    )


class DefaultOrdered(Model):
    one = fields.TextField()
    second = fields.IntField()

    class Meta:
        ordering = ["one", "second"]


class FKToDefaultOrdered(Model):
    link: fields.ForeignKeyRelation[DefaultOrdered] = fields.ForeignKeyField(
        "models.DefaultOrdered", related_name="related"
    )
    value = fields.IntField()


class DefaultOrderedDesc(Model):
    one = fields.TextField()
    second = fields.IntField()

    class Meta:
        ordering = ["-one"]


class SourceFieldPk(Model):
    id = fields.IntField(primary_key=True, source_field="counter")
    name = fields.CharField(max_length=255)


class DefaultOrderedInvalid(Model):
    one = fields.TextField()
    second = fields.IntField()

    class Meta:
        ordering = ["one", "third"]


class School(Model):
    uuid = fields.UUIDField(primary_key=True)
    name = fields.TextField()
    id = fields.IntField(unique=True)

    students: fields.ReverseRelation["Student"]
    principal: fields.ReverseRelation["Principal"]


class Student(Model):
    id = fields.IntField(primary_key=True)
    name = fields.TextField()
    school: fields.ForeignKeyRelation[School] = fields.ForeignKeyField(
        "models.School", related_name="students", to_field="id"
    )


class Principal(Model):
    id = fields.IntField(primary_key=True)
    name = fields.TextField()
    school: fields.OneToOneRelation[School] = fields.OneToOneField(
        "models.School",
        on_delete=fields.CASCADE,
        related_name="principal",
        to_field="id",
    )


class Signals(Model):
    name = fields.CharField(max_length=255)


class DefaultUpdate(Model):
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)


class DefaultModel(Model):
    int_default = fields.IntField(default=1)
    float_default = fields.FloatField(default=1.5)
    decimal_default = fields.DecimalField(max_digits=8, decimal_places=2, default=Decimal(1))
    bool_default = fields.BooleanField(default=True)
    char_default = fields.CharField(max_length=20, default="tortoise")
    date_default = fields.DateField(default=datetime.date(year=2020, month=5, day=21))
    datetime_default = fields.DatetimeField(
        default=datetime.datetime(year=2020, month=5, day=20, tzinfo=pytz.utc)
    )


class RequiredPKModel(Model):
    id = fields.CharField(primary_key=True, max_length=100)
    name = fields.CharField(max_length=255)


class ValidatorModel(Model):
    regex = fields.CharField(max_length=100, null=True, validators=[RegexValidator("abc.+", re.I)])
    max_length = fields.CharField(max_length=5, null=True)
    ipv4 = fields.CharField(max_length=100, null=True, validators=[validate_ipv4_address])
    ipv6 = fields.CharField(max_length=100, null=True, validators=[validate_ipv6_address])
    max_value = fields.IntField(null=True, validators=[MaxValueValidator(20.0)])
    min_value = fields.IntField(null=True, validators=[MinValueValidator(10.0)])
    max_value_decimal = fields.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        validators=[MaxValueValidator(Decimal("2.0"))],
    )
    min_value_decimal = fields.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        validators=[MinValueValidator(Decimal("1.0"))],
    )
    comma_separated_integer_list = fields.CharField(
        max_length=100, null=True, validators=[CommaSeparatedIntegerListValidator()]
    )


class NumberSourceField(Model):
    number = fields.IntField(source_field="counter", default=0)


class StatusQuerySet(QuerySet):
    def active(self):
        return self.filter(status=1)


class StatusManager(Manager):
    def __init__(self, model=None, queryset_cls=None) -> None:
        super().__init__(model=model)
        self.queryset_cls = queryset_cls or QuerySet

    def get_queryset(self):
        return self.queryset_cls(self._model)


class AbstractManagerModel(Model):
    all_objects = Manager()
    status = fields.IntField(default=0)

    class Meta:
        manager = StatusManager()
        abstract = True


class User(Model):
    id = fields.IntField(primary_key=True)
    username = fields.CharField(max_length=32)
    mail = fields.CharField(max_length=64)
    bio = fields.TextField()


class ManagerModel(AbstractManagerModel):
    class Meta:
        manager = StatusManager(queryset_cls=StatusQuerySet)


class ManagerModelExtra(AbstractManagerModel):
    extra = fields.CharField(max_length=200)


class Extra(Model):
    """Dumb model, has no fk.
    src: https://github.com/tortoise/tortoise-orm/pull/826#issuecomment-883341557
    """

    id = fields.IntField(primary_key=True)
    # currently, tortoise don't save models with single pk field for some reason \_0_/
    some_name = fields.CharField(default=lambda: str(uuid.uuid4()), max_length=64)


class Single(Model):
    """Dumb model, having single fk
    src: https://github.com/tortoise/tortoise-orm/pull/826#issuecomment-883341557
    """

    id = fields.IntField(primary_key=True)
    extra: fields.ForeignKeyNullableRelation[Extra] = fields.ForeignKeyField(
        "models.Extra", related_name="singles", null=True
    )


class Pair(Model):
    """Dumb model, having double fk
    src: https://github.com/tortoise/tortoise-orm/pull/826#issuecomment-883341557
    """

    id = fields.IntField(primary_key=True)
    left: fields.ForeignKeyNullableRelation[Single] = fields.ForeignKeyField(
        "models.Single", related_name="lefts", null=True
    )
    right: fields.ForeignKeyNullableRelation[Single] = fields.ForeignKeyField(
        "models.Single", related_name="rights", null=True, on_delete=NO_ACTION
    )


class OldStyleModel(Model):
    id = fields.IntField(pk=True)
    external_id = fields.IntField(index=True)


def camelize_var(var_name: str):
    var_parts: List[str] = var_name.split("_")
    return var_parts[0] + "".join([part.title() for part in var_parts[1:]])


class CamelCaseAliasPerson(Model):
    """CamelCaseAliasPerson model.

    - A model that generates camelized aliases automatically by
        configuring config_class.
    """

    id = fields.IntField(primary_key=True)
    first_name = fields.CharField(max_length=255)
    last_name = fields.CharField(max_length=255)
    full_address = fields.TextField(null=True)

    class PydanticMeta:
        """Defines the default config for pydantic model generator."""

        model_config = ConfigDict(
            title="My custom title",
            extra="ignore",
            alias_generator=camelize_var,
            populate_by_name=True,
        )


def callable_default() -> str:
    return "callable_default"


async def async_callable_default() -> str:
    return "async_callable_default"


class CallableDefault(Model):
    id = fields.IntField(primary_key=True)
    callable_default = fields.CharField(max_length=32, default=callable_default)
    async_default = fields.CharField(max_length=32, default=async_callable_default)


class BenchmarkFewFields(Model):
    timestamp = fields.DatetimeField(auto_now_add=True)
    level = fields.SmallIntField(index=True)
    text = fields.CharField(max_length=255)


class BenchmarkManyFields(Model):
    timestamp = fields.DatetimeField(auto_now_add=True)
    level = fields.SmallIntField(index=True)
    text = fields.CharField(max_length=255)

    col_float1 = fields.FloatField(default=2.2)
    col_smallint1 = fields.SmallIntField(default=2)
    col_int1 = fields.IntField(default=2000000)
    col_bigint1 = fields.BigIntField(default=99999999)
    col_char1 = fields.CharField(max_length=255, default="value1")
    col_text1 = fields.TextField(default="Moo,Foo,Baa,Waa,Moo,Foo,Baa,Waa,Moo,Foo,Baa,Waa")
    col_decimal1 = fields.DecimalField(12, 8, default=Decimal("2.2"))
    col_json1 = fields.JSONField[dict](
        default={"a": 1, "b": "b", "c": [2], "d": {"e": 3}, "f": True}
    )

    col_float2 = fields.FloatField(null=True)
    col_smallint2 = fields.SmallIntField(null=True)
    col_int2 = fields.IntField(null=True)
    col_bigint2 = fields.BigIntField(null=True)
    col_char2 = fields.CharField(max_length=255, null=True)
    col_text2 = fields.TextField(null=True)
    col_decimal2 = fields.DecimalField(12, 8, null=True)
    col_json2 = fields.JSONField[dict](null=True)

    col_float3 = fields.FloatField(default=2.2)
    col_smallint3 = fields.SmallIntField(default=2)
    col_int3 = fields.IntField(default=2000000)
    col_bigint3 = fields.BigIntField(default=99999999)
    col_char3 = fields.CharField(max_length=255, default="value1")
    col_text3 = fields.TextField(default="Moo,Foo,Baa,Waa,Moo,Foo,Baa,Waa,Moo,Foo,Baa,Waa")
    col_decimal3 = fields.DecimalField(12, 8, default=Decimal("2.2"))
    col_json3 = fields.JSONField[dict](
        default={"a": 1, "b": "b", "c": [2], "d": {"e": 3}, "f": True}
    )

    col_float4 = fields.FloatField(null=True)
    col_smallint4 = fields.SmallIntField(null=True)
    col_int4 = fields.IntField(null=True)
    col_bigint4 = fields.BigIntField(null=True)
    col_char4 = fields.CharField(max_length=255, null=True)
    col_text4 = fields.TextField(null=True)
    col_decimal4 = fields.DecimalField(12, 8, null=True)
    col_json4 = fields.JSONField[dict](null=True)
