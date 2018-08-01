from tortoise.aggregation import Count
from tortoise.contrib import test
from tortoise.tests.testmodels import Event, Team, Tournament


class TestRelations(test.TestCase):
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

        self.assertEqual([team.id for team in event.participants], [])

        teamids = []
        async for team in event.participants:
            teamids.append(team.id)
        self.assertEqual(teamids, [participants[0].id, participants[1].id])

        self.assertEqual(
            [team.id for team in event.participants],
            [participants[0].id, participants[1].id]
        )

        self.assertEqual(event.participants[0].id, participants[0].id)

        selected_events = await Event.filter(
            participants=participants[0].id
        ).prefetch_related('participants', 'tournament')
        self.assertEqual(len(selected_events), 1)
        self.assertEqual(selected_events[0].tournament.id, tournament.id)
        self.assertEqual(len(selected_events[0].participants), 2)
        await participants[0].fetch_related('events')
        self.assertEqual(participants[0].events[0], event)

        await Team.fetch_for_list(participants, 'events')

        await Team.filter(events__tournament__id=tournament.id)

        await Event.filter(tournament=tournament)

        await Tournament.filter(events__name__in=['Test', 'Prod']).distinct()

        result = await Event.filter(id=event.id).values('id', 'name', tournament='tournament__name')
        self.assertEqual(result[0]['tournament'], tournament.name)

        result = await Event.filter(id=event.id).values_list('id', 'participants__name')
        self.assertEqual(len(result), 2)

    async def test_reset_queryset_on_query(self):
        tournament = await Tournament.create(name='New Tournament')
        event = await Event.create(name='Test', tournament_id=tournament.id)
        participants = []
        for i in range(2):
            team = await Team.create(name='Team {}'.format(i + 1))
            participants.append(team)
        await event.participants.add(*participants)
        queryset = Event.all().annotate(count=Count('participants'))
        await queryset.first()
        await queryset.filter(name='Test').first()
