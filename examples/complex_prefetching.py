import asyncio

from examples import get_db_name
from tortoise import Tortoise, fields
from tortoise.backends.sqlite.client import SqliteClient
from tortoise.models import Model
from tortoise.query_utils import Q, Prefetch
from tortoise.utils import generate_schema


class Tournament(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()

    def __str__(self):
        return self.name


class Event(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    tournament = fields.ForeignKeyField('models.Tournament', related_name='events')
    participants = fields.ManyToManyField('models.Team', related_name='events', through='event_team')

    def __str__(self):
        return self.name


class Team(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()

    def __str__(self):
        return self.name


async def run():
    db_name = get_db_name()
    client = SqliteClient(db_name)
    await client.create_connection()
    Tortoise.init(client)
    await generate_schema(client)

    tournament = await Tournament.create(name='tournament')
    await Event.create(name='First', tournament=tournament)
    await Event.create(name='Second', tournament=tournament)
    tournament_with_filtered = await Tournament.all().prefetch_related(
        Prefetch('events', queryset=Event.filter(name='First'))
    ).first()
    tournament = await Tournament.first().prefetch_related('events')
    assert len(tournament_with_filtered.events) == 1
    assert len(tournament.events) == 2


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
