"""
This example shows how relations between models work.

Key points in this example are use of ForeignKeyField and ManyToManyField
to declare relations and use of .prefetch_related() and .fetch_related()
to get this related objects
"""
import asyncio

from examples import get_db_name
from tortoise import Tortoise, fields
from tortoise.backends.sqlite.client import SqliteClient
from tortoise.exceptions import NoValuesFetched
from tortoise.models import Model
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

    tournament = Tournament(name='New Tournament')
    await tournament.save()
    await Event(name='Without participants', tournament_id=tournament.id).save()
    event = Event(name='Test', tournament_id=tournament.id)
    await event.save()
    participants = []
    for i in range(2):
        team = Team(name='Team {}'.format(i + 1))
        await team.save()
        participants.append(team)
    await event.participants.add(participants[0], participants[1])
    await event.participants.add(participants[0], participants[1])

    try:
        for team in event.participants:
            print(team.id)
    except NoValuesFetched:
        pass

    async for team in event.participants:
        print(team.id)

    for team in event.participants:
        print(team.id)

    assert event.participants[0].id == participants[0].id

    selected_events = await Event.filter(
        participants=participants[0].id,
    ).prefetch_related('participants', 'tournament')
    assert len(selected_events) == 1
    assert selected_events[0].tournament.id == tournament.id
    assert len(selected_events[0].participants) == 2
    await participants[0].fetch_related('events')
    assert participants[0].events[0] == event

    await Team.fetch_for_list(participants, 'events')

    await Team.filter(events__tournament__id=tournament.id)

    await Event.filter(tournament=tournament)

    await Tournament.filter(
        events__name__in=['Test', 'Prod'],
    ).order_by('-events__participants__name').distinct()

    result = await Event.filter(id=event.id).values('id', 'name', tournament='tournament__name')
    assert result[0]['tournament'] == tournament.name

    result = await Event.filter(id=event.id).values_list('id', 'participants__name')
    assert len(result) == 2


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
