"""
This example shows how relations between models work.

Key points in this example are use of ForeignKeyField and ManyToManyField
to declare relations and use of .prefetch_related() and .fetch_related()
to get this related objects
"""
import asyncio

from tortoise import Tortoise, fields
from tortoise.exceptions import NoValuesFetched
from tortoise.models import Model


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
    await Tortoise.init(config_file='config.json')
    await Tortoise.generate_schemas()

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

    print(await Event.filter(
        participants=participants[0].id,
    ).prefetch_related('participants', 'tournament'))
    print(await participants[0].fetch_related('events'))

    print(await Team.fetch_for_list(participants, 'events'))

    print(await Team.filter(events__tournament__id=tournament.id))

    print(await Event.filter(tournament=tournament))

    print(await Tournament.filter(
        events__name__in=['Test', 'Prod'],
    ).order_by('-events__participants__name').distinct())

    print(await Event.filter(id=event.id).values('id', 'name', tournament='tournament__name'))

    print(await Event.filter(id=event.id).values_list('id', 'participants__name'))


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
