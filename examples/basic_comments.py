"""
This example demonstrates most basic operations with single model
and a Table definition generation with comment support
"""
import asyncio

from tortoise import Tortoise, fields
from tortoise.models import Model


class Event(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField(description="Name of the event that corresponds to an action")
    datetime = fields.DatetimeField(null=True, description="Datetime of when the event was generated")

    class Meta:
        table = "event"
        table_description = "This table contains a list of all the example events"

    def __str__(self):
        return self.name


async def run():
    await Tortoise.init(config_file="config.json")
    await Tortoise.generate_schemas()

    event = await Event.create(name="Test")
    await Event.filter(id=event.id).update(name="Updated name")

    print(await Event.filter(name="Updated name").first())

    await Event(name="Test 2").save()
    print(await Event.all().values_list("id", flat=True))
    print(await Event.all().values("id", "name"))


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
