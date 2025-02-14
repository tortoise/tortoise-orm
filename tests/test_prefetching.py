from tests.testmodels import Address, Event, Team, Tournament
from tortoise.contrib import test
from tortoise.exceptions import FieldError, OperationalError
from tortoise.functions import Count
from tortoise.query_utils import Prefetch


class TestPrefetching(test.TestCase):
    async def test_prefetch(self):
        tournament = await Tournament.create(name="tournament")
        event = await Event.create(name="First", tournament=tournament)
        await Event.create(name="Second", tournament=tournament)
        team = await Team.create(name="1")
        team_second = await Team.create(name="2")
        await event.participants.add(team, team_second)
        tournament = await Tournament.all().prefetch_related("events__participants").first()
        self.assertEqual(len(tournament.events[0].participants), 2)
        self.assertEqual(len(tournament.events[1].participants), 0)

    async def test_prefetch_object(self):
        tournament = await Tournament.create(name="tournament")
        await Event.create(name="First", tournament=tournament)
        await Event.create(name="Second", tournament=tournament)
        tournament_with_filtered = (
            await Tournament.all()
            .prefetch_related(Prefetch("events", queryset=Event.filter(name="First")))
            .first()
        )
        tournament = await Tournament.first().prefetch_related("events")
        self.assertEqual(len(tournament_with_filtered.events), 1)
        self.assertEqual(len(tournament.events), 2)

    async def test_prefetch_unknown_field(self):
        with self.assertRaises(OperationalError):
            tournament = await Tournament.create(name="tournament")
            await Event.create(name="First", tournament=tournament)
            await Event.create(name="Second", tournament=tournament)
            await (
                Tournament.all()
                .prefetch_related(Prefetch("events1", queryset=Event.filter(name="First")))
                .first()
            )

    async def test_prefetch_m2m(self):
        tournament = await Tournament.create(name="tournament")
        event = await Event.create(name="First", tournament=tournament)
        team = await Team.create(name="1")
        team_second = await Team.create(name="2")
        await event.participants.add(team, team_second)
        fetched_events = (
            await Event.all()
            .prefetch_related(Prefetch("participants", queryset=Team.filter(name="1")))
            .first()
        )
        self.assertEqual(len(fetched_events.participants), 1)

    async def test_prefetch_o2o(self):
        tournament = await Tournament.create(name="tournament")
        event = await Event.create(name="First", tournament=tournament)
        await Address.create(city="Santa Monica", street="Ocean", event=event)

        fetched_events = await Event.all().prefetch_related("address").first()

        self.assertEqual(fetched_events.address.city, "Santa Monica")

    async def test_prefetch_nested(self):
        tournament = await Tournament.create(name="tournament")
        event = await Event.create(name="First", tournament=tournament)
        await Event.create(name="Second", tournament=tournament)
        team = await Team.create(name="1")
        team_second = await Team.create(name="2")
        await event.participants.add(team, team_second)
        fetched_tournaments = (
            await Tournament.all()
            .prefetch_related(
                Prefetch("events", queryset=Event.filter(name="First")),
                Prefetch("events__participants", queryset=Team.filter(name="1")),
            )
            .first()
        )
        self.assertEqual(len(fetched_tournaments.events[0].participants), 1)

    async def test_prefetch_nested_with_aggregation(self):
        tournament = await Tournament.create(name="tournament")
        event = await Event.create(name="First", tournament=tournament)
        await Event.create(name="Second", tournament=tournament)
        team = await Team.create(name="1")
        team_second = await Team.create(name="2")
        await event.participants.add(team, team_second)
        fetched_tournaments = (
            await Tournament.all()
            .prefetch_related(
                Prefetch(
                    "events", queryset=Event.annotate(teams=Count("participants")).filter(teams=2)
                )
            )
            .first()
        )
        self.assertEqual(len(fetched_tournaments.events), 1)
        self.assertEqual(fetched_tournaments.events[0].pk, event.pk)

    async def test_prefetch_direct_relation(self):
        tournament = await Tournament.create(name="tournament")
        await Event.create(name="First", tournament=tournament)
        event = await Event.first().prefetch_related("tournament")
        self.assertEqual(event.tournament.id, tournament.id)

    async def test_prefetch_bad_key(self):
        tournament = await Tournament.create(name="tournament")
        await Event.create(name="First", tournament=tournament)
        with self.assertRaisesRegex(FieldError, "Relation tour1nament for models.Event not found"):
            await Event.first().prefetch_related("tour1nament")

    async def test_prefetch_m2m_filter(self):
        tournament = await Tournament.create(name="tournament")
        team = await Team.create(name="1")
        team_second = await Team.create(name="2")
        event = await Event.create(name="First", tournament=tournament)
        await event.participants.add(team, team_second)
        event = await Event.first().prefetch_related(
            Prefetch("participants", Team.filter(name="2"))
        )
        self.assertEqual(len(event.participants), 1)
        self.assertEqual(list(event.participants), [team_second])

    async def test_prefetch_m2m_to_attr(self):
        tournament = await Tournament.create(name="tournament")
        team = await Team.create(name="1")
        team_second = await Team.create(name="2")
        event = await Event.create(name="First", tournament=tournament)
        await event.participants.add(team, team_second)
        event = await Event.first().prefetch_related(
            Prefetch("participants", Team.filter(name="1"), to_attr="to_attr_participants_1"),
            Prefetch("participants", Team.filter(name="2"), to_attr="to_attr_participants_2"),
        )
        self.assertEqual(list(event.to_attr_participants_1), [team])
        self.assertEqual(list(event.to_attr_participants_2), [team_second])

    async def test_prefetch_o2o_to_attr(self):
        tournament = await Tournament.create(name="tournament")
        event = await Event.create(name="First", tournament=tournament)
        address = await Address.create(city="Santa Monica", street="Ocean", event=event)
        event = await Event.get(pk=event.pk).prefetch_related(
            Prefetch("address", to_attr="to_address", queryset=Address.all())
        )
        self.assertEqual(address.pk, event.to_address.pk)

    async def test_prefetch_direct_relation_to_attr(self):
        tournament = await Tournament.create(name="tournament")
        await Event.create(name="First", tournament=tournament)
        event = await Event.first().prefetch_related(
            Prefetch("tournament", queryset=Tournament.all(), to_attr="to_attr_tournament")
        )
        self.assertEqual(event.to_attr_tournament.id, tournament.id)
