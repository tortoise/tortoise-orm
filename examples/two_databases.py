import asyncio

from examples import create_example_database
from tortoise import Tortoise, fields
from tortoise.backends.sqlite.client import SqliteClient
from tortoise.models import Model

"""
This example demonstrates how you can use Tortoise if you have to
separate databases

Disclaimer: Although it allows to use two databases, you can't
use relations between two databases

Key notes of this example is using db_route for Tortoise init
and explicitly declaring model apps in class Meta
"""


class Tournament(Model):
    id = fields.IntField(generated=True)
    name = fields.StringField()

    def __str__(self):
        return self.name

    class Meta:
        app = 'tournaments'


class Event(Model):
    id = fields.IntField(generated=True)
    name = fields.StringField()
    tournament_id = fields.IntField()
    # Here we make link to events.Team, not models.Team
    participants = fields.ManyToManyField('events.Team', related_name='events', through='event_team')

    def __str__(self):
        return self.name

    class Meta:
        app = 'events'


class Team(Model):
    id = fields.IntField(generated=True)
    name = fields.StringField()

    def __str__(self):
        return self.name

    class Meta:
        app = 'events'


async def run():
    db_name = create_example_database()
    second_db_name = create_example_database()
    client = SqliteClient(db_name)
    await client.create_connection()
    second_client = SqliteClient(second_db_name)
    Tortoise.init(db_routing={
        'tournaments': client,
        'events': second_client,
    })
    await Tournament(name='Tournament').save()
    await Event(name='Event').save()

    results = await client.execute_query('SELECT * FROM "event"')
    assert not results
    results = await second_client.execute_query('SELECT * FROM "event"')
    assert results


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
