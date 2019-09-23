from tests.testmodels import Employee, Event, Team, Tournament
from tortoise.aggregation import Count
from tortoise.contrib import test
from tortoise.exceptions import FieldError, NoValuesFetched


class TestRelations(test.TestCase):
    async def test_relations(self):
        tournament = Tournament(name="New Tournament")
        await tournament.save()
        await Event(name="Without participants", tournament_id=tournament.id).save()
        event = Event(name="Test", tournament_id=tournament.id)
        await event.save()
        participants = []
        for i in range(2):
            team = Team(name=f"Team {(i + 1)}")
            await team.save()
            participants.append(team)
        await event.participants.add(participants[0], participants[1])
        await event.participants.add(participants[0], participants[1])

        with self.assertRaises(NoValuesFetched):
            [team.id for team in event.participants]  # pylint: disable=W0104

        teamids = []
        async for team in event.participants:
            teamids.append(team.id)
        self.assertEqual(teamids, [participants[0].id, participants[1].id])
        teamids = [team.id async for team in event.participants]
        self.assertEqual(teamids, [participants[0].id, participants[1].id])

        self.assertEqual(
            [team.id for team in event.participants], [participants[0].id, participants[1].id]
        )

        self.assertEqual(event.participants[0].id, participants[0].id)

        selected_events = await Event.filter(participants=participants[0].id).prefetch_related(
            "participants", "tournament"
        )
        self.assertEqual(len(selected_events), 1)
        self.assertEqual(selected_events[0].tournament.id, tournament.id)
        self.assertEqual(len(selected_events[0].participants), 2)
        await participants[0].fetch_related("events")
        self.assertEqual(participants[0].events[0], event)

        await Team.fetch_for_list(participants, "events")

        await Team.filter(events__tournament__id=tournament.id)

        await Event.filter(tournament=tournament)

        await Tournament.filter(events__name__in=["Test", "Prod"]).distinct()

        result = await Event.filter(id=event.id).values("id", "name", tournament="tournament__name")
        self.assertEqual(result[0]["tournament"], tournament.name)

        result = await Event.filter(id=event.id).values_list("id", "participants__name")
        self.assertEqual(len(result), 2)

    async def test_reset_queryset_on_query(self):
        tournament = await Tournament.create(name="New Tournament")
        event = await Event.create(name="Test", tournament_id=tournament.id)
        participants = []
        for i in range(2):
            team = await Team.create(name=f"Team {(i + 1)}")
            participants.append(team)
        await event.participants.add(*participants)
        queryset = Event.all().annotate(count=Count("participants"))
        await queryset.first()
        await queryset.filter(name="Test").first()

    async def test_bool_for_relation_new_object(self):
        tournament = await Tournament.create(name="New Tournament")

        with self.assertRaises(NoValuesFetched):
            bool(tournament.events)

    async def test_bool_for_relation_old_object(self):
        await Tournament.create(name="New Tournament")
        tournament = await Tournament.first()

        with self.assertRaises(NoValuesFetched):
            bool(tournament.events)

    async def test_bool_for_relation_fetched_false(self):
        tournament = await Tournament.create(name="New Tournament")
        await tournament.fetch_related("events")

        self.assertFalse(bool(tournament.events))

    async def test_bool_for_relation_fetched_true(self):
        tournament = await Tournament.create(name="New Tournament")
        await Event.create(name="Test", tournament_id=tournament.id)
        await tournament.fetch_related("events")

        self.assertTrue(bool(tournament.events))

    async def test_m2m_add(self):
        tournament = await Tournament.create(name="tournament")
        event = await Event.create(name="First", tournament=tournament)
        team = await Team.create(name="1")
        team_second = await Team.create(name="2")
        await event.participants.add(team, team_second)
        fetched_event = await Event.first().prefetch_related("participants")
        self.assertEqual(len(fetched_event.participants), 2)

    async def test_m2m_add_already_added(self):
        tournament = await Tournament.create(name="tournament")
        event = await Event.create(name="First", tournament=tournament)
        team = await Team.create(name="1")
        team_second = await Team.create(name="2")
        await event.participants.add(team, team_second)
        await event.participants.add(team, team_second)
        fetched_event = await Event.first().prefetch_related("participants")
        self.assertEqual(len(fetched_event.participants), 2)

    async def test_m2m_clear(self):
        tournament = await Tournament.create(name="tournament")
        event = await Event.create(name="First", tournament=tournament)
        team = await Team.create(name="1")
        team_second = await Team.create(name="2")
        await event.participants.add(team, team_second)
        await event.participants.clear()
        fetched_event = await Event.first().prefetch_related("participants")
        self.assertEqual(len(fetched_event.participants), 0)

    async def test_m2m_remove(self):
        tournament = await Tournament.create(name="tournament")
        event = await Event.create(name="First", tournament=tournament)
        team = await Team.create(name="1")
        team_second = await Team.create(name="2")
        await event.participants.add(team, team_second)
        await event.participants.remove(team)
        fetched_event = await Event.first().prefetch_related("participants")
        self.assertEqual(len(fetched_event.participants), 1)

    async def test_m2m_remove_two(self):
        tournament = await Tournament.create(name="tournament")
        event = await Event.create(name="First", tournament=tournament)
        team = await Team.create(name="1")
        team_second = await Team.create(name="2")
        await event.participants.add(team, team_second)
        await event.participants.remove(team, team_second)
        fetched_event = await Event.first().prefetch_related("participants")
        self.assertEqual(len(fetched_event.participants), 0)

    async def test_self_ref(self):
        self.maxDiff = None
        root = await Employee.create(name="Root")
        loose = await Employee.create(name="Loose")
        _1 = await Employee.create(name="1. First H1", manager=root)
        _2 = await Employee.create(name="2. Second H1", manager=root)
        _1_1 = await Employee.create(name="1.1. First H2", manager=_1)
        _1_1_1 = await Employee.create(name="1.1.1. First H3", manager=_1_1)
        _2_1 = await Employee.create(name="2.1. Second H2", manager=_2)
        _2_2 = await Employee.create(name="2.2. Third H2", manager=_2)

        await _1.talks_to.add(_2, _1_1_1, loose)
        await _2_1.gets_talked_to.add(_2_2, _1_1, loose)

        LOOSE_TEXT = "Loose (to: 2.1. Second H2) (from: 1. First H1)"
        ROOT_TEXT = """Root (to: ) (from: )
  1. First H1 (to: 1.1.1. First H3, 2. Second H1, Loose) (from: )
    1.1. First H2 (to: 2.1. Second H2) (from: )
      1.1.1. First H3 (to: ) (from: 1. First H1)
  2. Second H1 (to: ) (from: 1. First H1)
    2.1. Second H2 (to: ) (from: 1.1. First H2, 2.2. Third H2, Loose)
    2.2. Third H2 (to: 2.1. Second H2) (from: )"""

        # Evaluated off creation objects
        self.assertEqual(await loose.full_hierarchy__async_for(), LOOSE_TEXT)
        self.assertEqual(await loose.full_hierarchy__fetch_related(), LOOSE_TEXT)
        self.assertEqual(await root.full_hierarchy__async_for(), ROOT_TEXT)
        self.assertEqual(await root.full_hierarchy__fetch_related(), ROOT_TEXT)

        # Evaluated off new objects → Result is identical
        root2 = await Employee.get(name="Root")
        loose2 = await Employee.get(name="Loose")
        self.assertEqual(await loose2.full_hierarchy__async_for(), LOOSE_TEXT)
        self.assertEqual(await loose2.full_hierarchy__fetch_related(), LOOSE_TEXT)
        self.assertEqual(await root2.full_hierarchy__async_for(), ROOT_TEXT)
        self.assertEqual(await root2.full_hierarchy__fetch_related(), ROOT_TEXT)

    async def test_prefetch_related_fk(self):
        tournament = await Tournament.create(name="New Tournament")
        await Event.create(name="Test", tournament_id=tournament.id)

        event2 = await Event.filter(name="Test").prefetch_related("tournament")
        self.assertEqual(event2[0].tournament, tournament)

    async def test_prefetch_related_rfk(self):
        tournament = await Tournament.create(name="New Tournament")
        event = await Event.create(name="Test", tournament_id=tournament.id)

        tournament2 = await Tournament.filter(name="New Tournament").prefetch_related("events")
        self.assertEqual(list(tournament2[0].events), [event])

    async def test_prefetch_related_missing_field(self):
        tournament = await Tournament.create(name="New Tournament")
        await Event.create(name="Test", tournament_id=tournament.id)

        with self.assertRaisesRegex(FieldError, "Relation tourn1ment for event not found"):
            await Event.filter(name="Test").prefetch_related("tourn1ment")

    async def test_prefetch_related_nonrel_field(self):
        tournament = await Tournament.create(name="New Tournament")
        await Event.create(name="Test", tournament_id=tournament.id)

        with self.assertRaisesRegex(FieldError, "Field modified on event is not a relation"):
            await Event.filter(name="Test").prefetch_related("modified")

    async def test_prefetch_related_id(self):
        tournament = await Tournament.create(name="New Tournament")
        await Event.create(name="Test", tournament_id=tournament.id)

        with self.assertRaisesRegex(FieldError, "Field id on event is not a relation"):
            await Event.filter(name="Test").prefetch_related("id")
