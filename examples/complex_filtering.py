import asyncio

from examples import create_example_database
from tortoise import Tortoise, fields
from tortoise.backends.sqlite.client import SqliteClient
from tortoise.models import Model
from tortoise.query_utils import Q

"""
This example shows some more complex querying

Key points are filtering by related names and using Q objects
"""


class Tournament(Model):
    id = fields.IntField(generated=True)
    name = fields.StringField()

    def __str__(self):
        return self.name


class Event(Model):
    id = fields.IntField(generated=True)
    name = fields.StringField()
    tournament = fields.ForeignKeyField('models.Tournament', related_name='events')
    participants = fields.ManyToManyField('models.Team', related_name='events', through='event_team')

    def __str__(self):
        return self.name


class Team(Model):
    id = fields.IntField(generated=True)
    name = fields.StringField()

    def __str__(self):
        return self.name


async def run():
    db_name = create_example_database()
    client = SqliteClient(db_name)
    await client.create_connection()
    Tortoise.init(client)

    tournament = Tournament(name='Tournament')
    await tournament.save()

    event_first = Event(name='1')
    await event_first.save()
    event_second = Event(name='2')
    await event_second.save()
    event_third = Event(name='3')
    await event_third.save()
    event_forth = Event(name='4')
    await event_forth.save()

    team_first = Team(name='First')
    await team_first.save()
    team_second = Team(name='Second')
    await team_second.save()

    await team_first.events.add(event_first)
    await event_second.participants.add(team_second)

    found_events = await Event.filter(
        Q(id__in=[event_first.id, event_second.id]) | Q(name='3')
    ).filter(participants__not=team_second.id)
    assert len(found_events) == 2
    assert found_events[0].id == event_first.id and found_events[1].id == event_third.id


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
