"""
This file contains the code that is meant to be checked by a type checker, not to be run as a test.
"""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum, IntEnum
from uuid import UUID

from tortoise.fields.data import (
    BinaryField,
    BooleanField,
    CharEnumField,
    CharField,
    DateField,
    DatetimeField,
    DecimalField,
    FloatField,
    IntEnumField,
    IntField,
    TimeDeltaField,
    TimeField,
    UUIDField,
)
from tortoise.models import Model


class Status(IntEnum):
    PENDING = 1
    ACTIVE = 2
    INACTIVE = 3


class Color(str, Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class InheretedFromIntField(IntField):
    pass


class TypeTestModel(Model):
    # CharField fields
    char_non_null = CharField(max_length=100, null=False)
    char_nullable = CharField(max_length=100, null=True)

    # IntField fields
    int_non_null = IntField(null=False)
    int_nullable = IntField(null=True)

    # BooleanField fields
    bool_non_null = BooleanField(null=False)
    bool_nullable = BooleanField(null=True)

    # DecimalField fields
    decimal_non_null = DecimalField(max_digits=10, decimal_places=2, null=False)
    decimal_nullable = DecimalField(max_digits=10, decimal_places=2, null=True)

    # DatetimeField fields
    datetime_non_null = DatetimeField(null=False)
    datetime_nullable = DatetimeField(null=True)

    # DateField fields
    date_non_null = DateField(null=False)
    date_nullable = DateField(null=True)

    # TimeField fields
    time_non_null = TimeField(null=False)
    time_nullable = TimeField(null=True)

    # TimeDeltaField fields
    timedelta_non_null = TimeDeltaField(null=False)
    timedelta_nullable = TimeDeltaField(null=True)

    # FloatField fields
    float_non_null = FloatField(null=False)
    float_nullable = FloatField(null=True)

    # UUIDField fields
    uuid_non_null = UUIDField(null=False)
    uuid_nullable = UUIDField(null=True)

    # BinaryField fields
    binary_non_null = BinaryField(null=False)
    binary_nullable = BinaryField(null=True)

    # Enum fields
    int_enum_field_non_null = IntEnumField(enum_type=Status, null=False)
    int_enum_field_nullable = IntEnumField(enum_type=Status, null=True)
    char_enum_field_non_null = CharEnumField(enum_type=Color, max_length=10, null=False)
    char_enum_field_nullable = CharEnumField(enum_type=Color, max_length=10, null=True)

    # inherited fields
    inhereted_int_field_non_null = InheretedFromIntField(null=False)
    inhereted_int_field_nullable = InheretedFromIntField(null=True)


def test_char_field_nullability() -> None:
    o = TypeTestModel(char_non_null="test", char_nullable="test")
    o.char_nullable = None
    o.char_non_null = "another test"


def test_int_field_nullability() -> None:
    o = TypeTestModel(char_non_null="test", int_non_null=42, int_nullable=42)
    o.int_nullable = None
    o.int_non_null = 100


def test_bool_field_nullability() -> None:
    o = TypeTestModel(char_non_null="test", bool_non_null=True, bool_nullable=True)
    o.bool_nullable = None
    o.bool_non_null = False


def test_decimal_field_nullability() -> None:
    o = TypeTestModel(
        char_non_null="test", decimal_non_null=Decimal("10.50"), decimal_nullable=Decimal("10.50")
    )
    o.decimal_nullable = None
    o.decimal_non_null = Decimal("20.75")


def test_datetime_field_nullability() -> None:
    now = datetime.now()
    o = TypeTestModel(char_non_null="test", datetime_non_null=now, datetime_nullable=now)
    o.datetime_nullable = None
    o.datetime_non_null = datetime(2024, 1, 1, 12, 0, 0)


def test_date_field_nullability() -> None:
    today = date.today()
    o = TypeTestModel(char_non_null="test", date_non_null=today, date_nullable=today)
    o.date_nullable = None
    o.date_non_null = date(2024, 1, 1)


def test_time_field_nullability() -> None:
    now_time = time(12, 0, 0)
    o = TypeTestModel(char_non_null="test", time_non_null=now_time, time_nullable=now_time)
    o.time_nullable = None
    o.time_non_null = time(15, 30, 0)


def test_timedelta_field_nullability() -> None:
    delta = timedelta(days=1)
    o = TypeTestModel(char_non_null="test", timedelta_non_null=delta, timedelta_nullable=delta)
    o.timedelta_nullable = None
    o.timedelta_non_null = timedelta(days=2)


def test_float_field_nullability() -> None:
    o = TypeTestModel(char_non_null="test", float_non_null=1.5, float_nullable=1.5)
    o.float_nullable = None
    o.float_non_null = 3.14


def test_uuid_field_nullability() -> None:
    test_uuid = UUID("12345678-1234-5678-1234-567812345678")
    o = TypeTestModel(char_non_null="test", uuid_non_null=test_uuid, uuid_nullable=test_uuid)
    o.uuid_nullable = None
    o.uuid_non_null = UUID("87654321-4321-8765-4321-876543218765")


def test_binary_field_nullability() -> None:
    o = TypeTestModel(char_non_null="test", binary_non_null=b"data", binary_nullable=b"data")
    o.binary_nullable = None
    o.binary_non_null = b"new data"


# TODO: add support for proper types when null=True for enum fields
# def test_enum_fields() -> None:
#     o = TypeTestModel(char_non_null="test", int_non_null=1, bool_non_null=True, float_non_null=1.0, binary_non_null=b"test")

#     o.int_enum_field_nullable = None
#     o.int_enum_field_non_null = Status.ACTIVE

#     o.char_enum_field_nullable = None
#     o.char_enum_field_non_null = Color.GREEN


def test_inhereted_int_field() -> None:
    o = TypeTestModel(
        char_non_null="test", inhereted_int_field_non_null=42, inhereted_int_field_nullable=42
    )
    o.inhereted_int_field_nullable = None
    o.inhereted_int_field_non_null = 100
