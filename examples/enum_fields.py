from enum import Enum, IntEnum

from tortoise import fields
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
