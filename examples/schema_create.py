import asyncio
import datetime
import secrets

from examples import get_db_name
from tortoise import Tortoise, fields
from tortoise.backends.sqlite.client import SqliteClient
from tortoise.models import Model
from tortoise.utils import generate_schema


class Tournament(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    created = fields.DatetimeField(auto_now_add=True)

    def __str__(self):
        return self.name


def generate_token():
    return secrets.token_hex(16)


class Event(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField(unique=True)
    tournament = fields.ForeignKeyField('models.Tournament', related_name='events')
    participants = fields.ManyToManyField(
        'models.Team', related_name='events', through='event_team'
    )
    modified = fields.DatetimeField(auto_now=True)
    prize = fields.DecimalField(max_digits=10, decimal_places=2, null=True)
    token = fields.TextField(default=generate_token)

    def __str__(self):
        return self.name


class Team(Model):
    id = fields.IntField(pk=True)
    name = fields.StringField()

    def __str__(self):
        return self.name


async def run():
    db_name = get_db_name()
    client = SqliteClient(db_name)
    await client.create_connection()
    Tortoise.init(client)
    await generate_schema(client)

    tournament = await Tournament.create(name='Test')
    assert tournament.created and tournament.created.date() == datetime.date.today()

    event = await Event.create(name='Test 1', tournament=tournament, prize=100)
    old_time = event.modified
    event.name = 'Test 2'
    await event.save()
    assert event.modified > old_time
    assert len(event.token) == 32


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
