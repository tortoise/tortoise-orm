"""
This example shows some more complex querying

Key points are filtering by related names and using Q objects
"""
import asyncio

from examples import get_db_name
from tortoise import Tortoise, fields
from tortoise.backends.sqlite.client import SqliteClient
from tortoise.models import Model
from tortoise.query_utils import Q
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
    participants = fields.ManyToManyField(
        'models.Team', related_name='events', through='event_team'
    )

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

    tournament = Tournament(name='Tournament')
    await tournament.save()

    second_tournament = Tournament(name='Tournament 2')
    await second_tournament.save()

    event_first = Event(name='1', tournament=tournament)
    await event_first.save()
    event_second = Event(name='2', tournament=second_tournament)
    await event_second.save()
    event_third = Event(name='3', tournament=tournament)
    await event_third.save()
    event_forth = Event(name='4', tournament=second_tournament)
    await event_forth.save()

    team_first = Team(name='First')
    await team_first.save()
    team_second = Team(name='Second')
    await team_second.save()

    await team_first.events.add(event_first)
    await event_second.participants.add(team_second)

    found_events = await Event.filter(Q(id__in=[event_first.id, event_second.id])
                                      | Q(name='3')).filter(participants__not=team_second.id
                                                            ).order_by('tournament__id').distinct()
    assert len(found_events) == 2
    assert found_events[0].id == event_first.id and found_events[1].id == event_third.id
    await Team.filter(events__tournament_id=tournament.id).order_by('-events__name')
    await Tournament.filter(events__name__in=['1', '3']
                            ).order_by('-events__participants__name').distinct()

    teams = await Team.filter(name__icontains='CON')
    assert len(teams) == 1 and teams[0].name == 'Second'

    tournaments = await Tournament.filter(events__participants__name__startswith='Fir')
    assert len(tournaments) == 1 and tournaments[0] == tournament
    assert await Tournament.filter(id__icontains=1).count() == 1


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
