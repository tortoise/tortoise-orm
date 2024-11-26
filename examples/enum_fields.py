from enum import Enum, IntEnum
from typing import Type, cast

from tortoise import Tortoise, fields, run_async
from tortoise.fields.data import IntEnumFieldMixin, IntEnumType, IntField
from tortoise.models import Model


class Service(IntEnum):
    python_programming = 1
    database_design = 2
    system_administration = 3


class Currency(str, Enum):
    HUF = "HUF"
    EUR = "EUR"
    USD = "USD"


class Protocol(IntEnum):
    A = 10000
    B = 80000  # >32767, beyond the 'le' value in fields.IntEnumFieldInstance.constraints


class IntEnumFieldInstance(IntEnumFieldMixin, IntField):
    pass


def IntEnumField(enum_type: Type[IntEnumType], **kwargs) -> IntEnumType:
    return cast(IntEnumType, IntEnumFieldInstance(enum_type, **kwargs))


class EnumFields(Model):
    currency: Currency = fields.CharEnumField(Currency, default=Currency.HUF)
    # When each value of the enum_type is between [-32768, 32767], use the fields.IntEnumField
    service: Service = fields.IntEnumField(Service)
    # Else, you can use a custom Field
    protocol: Protocol = IntEnumField(Protocol)


async def run():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["__main__"]})
    await Tortoise.generate_schemas()

    obj0 = await EnumFields.create(
        service=Service.python_programming, currency=Currency.USD, protocol=Protocol.A
    )
    # also you can use valid int and str value directly
    await EnumFields.create(service=1, currency="USD", protocol=Protocol.B.value)

    try:
        # invalid enum value will raise ValueError
        await EnumFields.create(service=4, currency="XXX")
    except ValueError:
        print("Value is invalid")

    await EnumFields.filter(pk=obj0.pk).update(
        service=Service.database_design, currency=Currency.HUF
    )
    # also you can use valid int and str value directly
    await EnumFields.filter(pk=obj0.pk).update(service=2, currency="HUF")


if __name__ == "__main__":
    run_async(run())
