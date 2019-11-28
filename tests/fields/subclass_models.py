from enum import Enum, IntEnum

from tests.fields.subclass_fields import EnumField, IntEnumField
from tortoise import fields
from tortoise.models import Model


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


class ContactTypeEnum(IntEnum):
    work = 1
    home = 2
    other = 3


class Contact(Model):
    id = fields.IntField(pk=True)
    type = IntEnumField(ContactTypeEnum, default=ContactTypeEnum.other)
