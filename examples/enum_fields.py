from enum import Enum, IntEnum

from tortoise import Tortoise, fields, run_async
from tortoise.models import Model


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


async def run():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["__main__"]})
    await Tortoise.generate_schemas()

    obj0 = await EnumFields.create(service=Service.python_programming, currency=Currency.USD)
    # also you can use valid int and str value directly
    await EnumFields.create(service=1, currency="USD")

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
