"""
This example shows how relations between models work.

Key points in this example are use of ForeignKeyField and ManyToManyField
to declare relations and use of .prefetch_related() and .fetch_related()
to get this related objects
"""
from uuid import uuid4

from tortoise import Tortoise, fields, run_async
from tortoise.models import Model


class Company(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    uuid = fields.UUIDField(unique=True, default=uuid4)

    employees: fields.ReverseRelation["Employee"]


class Employee(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    company: fields.ForeignKeyRelation[Company] = fields.ForeignKeyField(
        "models.Company", related_name="employees", to_field="uuid",
    )


async def run():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["__main__"]})
    await Tortoise.generate_schemas()

    company = Company(id=1, name="First Company")
    await company.save()
    # await Employee(name="Sang-Heon Jeon", company_id=company.uuid).save()


if __name__ == "__main__":
    run_async(run())
