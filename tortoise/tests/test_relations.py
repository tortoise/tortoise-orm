import asynctest

from tortoise.contrib.testing import TestCase
from tortoise.tests.testmodels import Event, Team, Tournament


class TestRelations(TestCase):
    @asynctest.strict
    async def test_relations(self):
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

        self.assertEquals([team.id for team in event.participants], [])

        teamids = []
        async for team in event.participants:
            teamids.append(team.id)
        self.assertEquals(teamids, [1, 2])

        self.assertEquals([team.id for team in event.participants], [1, 2])

        self.assertEquals(event.participants[0].id, participants[0].id)

        selected_events = await Event.filter(
            participants=participants[0].id
        ).prefetch_related('participants', 'tournament')
        self.assertEquals(len(selected_events), 1)
        self.assertEquals(selected_events[0].tournament.id, tournament.id)
        self.assertEquals(len(selected_events[0].participants), 2)
        await participants[0].fetch_related('events')
        self.assertEquals(participants[0].events[0], event)

        await Team.fetch_for_list(participants, 'events')

        await Team.filter(events__tournament__id=tournament.id)

        await Event.filter(tournament=tournament)

        await Tournament.filter(events__name__in=['Test', 'Prod']
                                ).order_by('-events__participants__name').distinct()

        result = await Event.filter(id=event.id).values('id', 'name', tournament='tournament__name')
        self.assertEquals(result[0]['tournament'], tournament.name)

        result = await Event.filter(id=event.id).values_list('id', 'participants__name')
        self.assertEquals(len(result), 2)
