import asyncio

from examples import create_example_database
from tortoise import Tortoise, fields
from tortoise.backends.sqlite.client import SqliteClient
from tortoise.models import Model

"""
This example demonstrates most basic operations with single model
"""


class Event(Model):
    id = fields.IntField(generated=True)
    name = fields.StringField()

    class Meta:
        table = 'event'

    def __str__(self):
        return self.name


async def run():
    db_name = create_example_database()
    client = SqliteClient(db_name)
    await client.create_connection()
    Tortoise.init(client)
    event = await Event.create(name='Test')
    await Event.filter(id=event.id).update(name='Updated name')
    saved_event = await Event.filter(name='Updated name').first()
    assert saved_event.id == event.id
    await Event(name='Test 2').save()
    await Event.all().values_list('id', flat=True)
    await Event.all().values('id', 'name')


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
