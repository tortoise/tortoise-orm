"""
This example demonstrates most basic operations with single model
"""

from tortoise import fields, run_async
from tortoise.contrib.test import init_memory_sqlite
from tortoise.models import Model


class Event(Model):
    id = fields.IntField(primary_key=True)
    name = fields.TextField()
    datetime = fields.DatetimeField(null=True)
    username = fields.CharField(max_length=150, unique=True, db_index=True)

    class Meta:
        table = "event"

    def __str__(self):
        return self.name


@init_memory_sqlite
async def run() -> None:
    event = await Event.create(name="Test", username="test")
    await Event.filter(id=event.id).update(name="Updated name")

    print(await Event.filter(username="test").first())
    # >>> Updated name

    await Event(name="Test 2", username="test2").save()
    print(await Event.all().values_list("id", flat=True))
    # >>> [1, 2]
    print(await Event.all().values("id", "name"))
    # >>> [{'id': 1, 'name': 'Updated name'}, {'id': 2, 'name': 'Test 2'}]


if __name__ == "__main__":
    run_async(run())
