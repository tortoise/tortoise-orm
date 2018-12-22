from tortoise.aggregation import Count
from tortoise.contrib import test
from tortoise.exceptions import OperationalError
from tortoise.query_utils import Prefetch
from tortoise.tests.testmodels import Event, Team, Tournament


class TestPrefetching(test.TestCase):
    async def test_prefetch(self):
        tournament = await Tournament.create(name='tournament')
        event = await Event.create(name='First', tournament=tournament)
        await Event.create(name='Second', tournament=tournament)
        team = await Team.create(name='1')
        team_second = await Team.create(name='2')
        await event.participants.add(team, team_second)
        tournament = await Tournament.all().prefetch_related('events__participants').first()
        self.assertEqual(len(tournament.events[0].participants), 2)
        self.assertEqual(len(tournament.events[1].participants), 0)

    async def test_prefetch_object(self):
        tournament = await Tournament.create(name='tournament')
        await Event.create(name='First', tournament=tournament)
        await Event.create(name='Second', tournament=tournament)
        tournament_with_filtered = await Tournament.all().prefetch_related(
            Prefetch('events', queryset=Event.filter(name='First'))
        ).first()
        tournament = await Tournament.first().prefetch_related('events')
        self.assertEqual(len(tournament_with_filtered.events), 1)
        self.assertEqual(len(tournament.events), 2)

    async def test_prefetch_unknown_field(self):
        with self.assertRaises(OperationalError):
            tournament = await Tournament.create(name='tournament')
            await Event.create(name='First', tournament=tournament)
            await Event.create(name='Second', tournament=tournament)
            await Tournament.all().prefetch_related(
                Prefetch('events1', queryset=Event.filter(name='First'))
            ).first()

    async def test_prefetch_m2m(self):
        tournament = await Tournament.create(name='tournament')
        event = await Event.create(name='First', tournament=tournament)
        team = await Team.create(name='1')
        team_second = await Team.create(name='2')
        await event.participants.add(team, team_second)
        fetched_events = await Event.all().prefetch_related(
            Prefetch('participants', queryset=Team.filter(name='1'))
        ).first()
        self.assertEqual(len(fetched_events.participants), 1)

    async def test_prefetch_nested(self):
        tournament = await Tournament.create(name='tournament')
        event = await Event.create(name='First', tournament=tournament)
        await Event.create(name='Second', tournament=tournament)
        team = await Team.create(name='1')
        team_second = await Team.create(name='2')
        await event.participants.add(team, team_second)
        fetched_tournaments = await Tournament.all().prefetch_related(
            Prefetch('events', queryset=Event.filter(name='First')),
            Prefetch('events__participants', queryset=Team.filter(name='1'))
        ).first()
        self.assertEqual(len(fetched_tournaments.events[0].participants), 1)

    async def test_prefetch_nested_with_aggregation(self):
        tournament = await Tournament.create(name='tournament')
        event = await Event.create(name='First', tournament=tournament)
        await Event.create(name='Second', tournament=tournament)
        team = await Team.create(name='1')
        team_second = await Team.create(name='2')
        await event.participants.add(team, team_second)
        fetched_tournaments = await Tournament.all().prefetch_related(
            Prefetch(
                'events',
                queryset=Event.annotate(teams=Count('participants')).filter(teams=2)
            )
        ).first()
        self.assertEqual(len(fetched_tournaments.events), 1)
        self.assertEqual(fetched_tournaments.events[0].id, event.id)

    async def test_prefetch_direct_relation(self):
        tournament = await Tournament.create(name='tournament')
        await Event.create(name='First', tournament=tournament)
        event = await Event.first().prefetch_related('tournament')
        self.assertEqual(event.tournament.id, tournament.id)
