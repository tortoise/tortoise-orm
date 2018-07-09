"""
This example demonstrates how you can use transactions with tortoise

Currently tortoise doesn't have some kind of magic transaction wrapper
like django's transaction.atomic, but if you have to make something in transaction
you could still do it like this
"""
import asyncio
import sqlite3

from tortoise import Tortoise, fields
from tortoise.backends.sqlite.client import SqliteClient
from tortoise.models import Model
from tortoise.utils import generate_schema


class Event(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()

    class Meta:
        table = 'event'

    def __str__(self):
        return self.name


async def run():
    client = SqliteClient('example_transaction.sqlite3')
    await client.create_connection()
    Tortoise.init(client)
    await generate_schema(client)

    try:
        async with client.in_transaction() as connection:
            event = Event(name='Test')
            await event.save(using_db=connection)
            await Event.filter(id=event.id).using_db(connection).update(name='Updated name')
            saved_event = await Event.filter(name='Updated name').using_db(connection).first()
            await connection.execute_query('SELECT * FROM non_existent_table')
    except sqlite3.OperationalError:
        pass
    saved_event = await Event.filter(name='Updated name').first()
    print(saved_event)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
