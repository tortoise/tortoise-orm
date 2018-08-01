"""
This example demonstrates most basic operations with single model
"""
import asyncio

from tortoise import Tortoise, fields
from tortoise.models import Model


class Event(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    datetime = fields.DatetimeField(null=True)

    class Meta:
        table = 'event'

    def __str__(self):
        return self.name


async def run():
    await Tortoise.init(config_file='config.json')
    await Tortoise.generate_schemas()

    event = await Event.create(name='Test')
    await Event.filter(id=event.id).update(name='Updated name')

    print(await Event.filter(name='Updated name').first())

    await Event(name='Test 2').save()
    print(await Event.all().values_list('id', flat=True))
    print(await Event.all().values('id', 'name'))


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
