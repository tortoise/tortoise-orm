from tests.testmodels import Event, IntFields, Reporter, Team, Tournament
from tortoise.contrib import test
from tortoise.expressions import F
from tortoise.functions import Coalesce, Count, Length, Lower, Max, Trim, Upper
from tortoise.query_utils import Q


class TestFiltering(test.TestCase):
    async def test_filtering(self):
        tournament = Tournament(name="Tournament")
        await tournament.save()

        second_tournament = Tournament(name="Tournament 2")
        await second_tournament.save()

        event_first = Event(name="1", tournament=tournament)
        await event_first.save()
        event_second = Event(name="2", tournament=second_tournament)
        await event_second.save()
        event_third = Event(name="3", tournament=tournament)
        await event_third.save()
        event_forth = Event(name="4", tournament=second_tournament)
        await event_forth.save()

        team_first = Team(name="First")
        await team_first.save()
        team_second = Team(name="Second")
        await team_second.save()

        await team_first.events.add(event_first)
        await event_second.participants.add(team_second)

        found_events = (
            await Event.filter(Q(pk__in=[event_first.pk, event_second.pk]) | Q(name="3"))
            .filter(participants__not=team_second.id)
            .order_by("name", "tournament_id")
            .distinct()
        )
        self.assertEqual(len(found_events), 2)
        self.assertEqual(found_events[0].pk, event_first.pk)
        self.assertEqual(found_events[1].pk, event_third.pk)
        await Team.filter(events__tournament_id=tournament.id).order_by("-events__name")
        await Tournament.filter(events__name__in=["1", "3"]).distinct()

        teams = await Team.filter(name__icontains="CON")
        self.assertEqual(len(teams), 1)
        self.assertEqual(teams[0].name, "Second")

        teams = await Team.filter(name__iexact="SeCoNd")
        self.assertEqual(len(teams), 1)
        self.assertEqual(teams[0].name, "Second")

        tournaments = await Tournament.filter(events__participants__name__startswith="Fir")
        self.assertEqual(len(tournaments), 1)
        self.assertEqual(tournaments[0], tournament)

    async def test_q_object_backward_related_query(self):
        await Tournament.create(name="0")
        tournament = await Tournament.create(name="Tournament")
        event = await Event.create(name="1", tournament=tournament)
        fetched_tournament = await Tournament.filter(events=event.event_id).first()
        self.assertEqual(fetched_tournament.id, tournament.id)

        fetched_tournament = await Tournament.filter(Q(events=event.event_id)).first()
        self.assertEqual(fetched_tournament.id, tournament.id)

    async def test_q_object_related_query(self):
        tournament_first = await Tournament.create(name="0")
        tournament_second = await Tournament.create(name="1")
        event = await Event.create(name="1", tournament=tournament_second)
        await Event.create(name="1", tournament=tournament_first)

        fetched_event = await Event.filter(tournament=tournament_second).first()
        self.assertEqual(fetched_event.pk, event.pk)

        fetched_event = await Event.filter(Q(tournament=tournament_second)).first()
        self.assertEqual(fetched_event.pk, event.pk)

        fetched_event = await Event.filter(Q(tournament=tournament_second.id)).first()
        self.assertEqual(fetched_event.pk, event.pk)

    async def test_null_filter(self):
        tournament = await Tournament.create(name="Tournament")
        reporter = await Reporter.create(name="John")
        await Event.create(name="2", tournament=tournament, reporter=reporter)
        event = await Event.create(name="1", tournament=tournament)
        fetched_events = await Event.filter(reporter=None)
        self.assertEqual(len(fetched_events), 1)
        self.assertEqual(fetched_events[0].pk, event.pk)

    async def test_exclude(self):
        await Tournament.create(name="0")
        tournament = await Tournament.create(name="1")

        tournaments = await Tournament.exclude(name="0")
        self.assertEqual(len(tournaments), 1)
        self.assertEqual(tournaments[0].name, tournament.name)

    async def test_exclude_with_filter(self):
        await Tournament.create(name="0")
        tournament = await Tournament.create(name="1")
        await Tournament.create(name="2")

        tournaments = await Tournament.exclude(name="0").filter(id=tournament.id)
        self.assertEqual(len(tournaments), 1)
        self.assertEqual(tournaments[0].name, tournament.name)

    async def test_filter_null_on_related(self):
        tournament = await Tournament.create(name="Tournament")
        reporter = await Reporter.create(name="John")
        event_first = await Event.create(name="1", tournament=tournament, reporter=reporter)
        event_second = await Event.create(name="2", tournament=tournament)

        team_first = await Team.create(name="1")
        team_second = await Team.create(name="2")
        await event_first.participants.add(team_first)
        await event_second.participants.add(team_second)

        fetched_teams = await Team.filter(events__reporter=None)
        self.assertEqual(len(fetched_teams), 1)
        self.assertEqual(fetched_teams[0].id, team_second.id)

    async def test_filter_or(self):
        await Tournament.create(name="0")
        await Tournament.create(name="1")
        await Tournament.create(name="2")

        tournaments = await Tournament.filter(Q(name="1") | Q(name="2"))
        self.assertEqual(len(tournaments), 2)
        self.assertSetEqual({t.name for t in tournaments}, {"1", "2"})

    async def test_filter_not(self):
        await Tournament.create(name="0")
        await Tournament.create(name="1")

        tournaments = await Tournament.filter(~Q(name="1"))
        self.assertEqual(len(tournaments), 1)
        self.assertEqual(tournaments[0].name, "0")

    async def test_filter_with_f_expression(self):
        await IntFields.create(intnum=1, intnum_null=1)
        await IntFields.create(intnum=2, intnum_null=1)
        self.assertEqual(await IntFields.filter(intnum=F("intnum_null")).count(), 1)
        self.assertEqual(await IntFields.filter(intnum__gte=F("intnum_null")).count(), 2)
        self.assertEqual(
            await IntFields.filter(intnum=F("intnum_null") + F("intnum_null")).count(), 1
        )

    async def test_filter_not_with_or(self):
        await Tournament.create(name="0")
        await Tournament.create(name="1")
        await Tournament.create(name="2")

        tournaments = await Tournament.filter(Q(name="1") | ~Q(name="2"))
        self.assertEqual(len(tournaments), 2)
        self.assertSetEqual({t.name for t in tournaments}, {"0", "1"})

    async def test_filter_by_aggregation_field(self):
        tournament = await Tournament.create(name="0")
        await Tournament.create(name="1")
        await Event.create(name="2", tournament=tournament)

        tournaments = await Tournament.annotate(events_count=Count("events")).filter(events_count=1)
        self.assertEqual(len(tournaments), 1)
        self.assertEqual(tournaments[0].id, tournament.id)

    async def test_filter_by_aggregation_field_with_and(self):
        tournament = await Tournament.create(name="0")
        tournament_second = await Tournament.create(name="1")
        await Event.create(name="1", tournament=tournament)
        await Event.create(name="2", tournament=tournament_second)

        tournaments = await Tournament.annotate(events_count=Count("events")).filter(
            events_count=1, name="0"
        )
        self.assertEqual(len(tournaments), 1)
        self.assertEqual(tournaments[0].id, tournament.id)

    async def test_filter_by_aggregation_field_with_and_as_one_node(self):
        tournament = await Tournament.create(name="0")
        tournament_second = await Tournament.create(name="1")
        await Event.create(name="1", tournament=tournament)
        await Event.create(name="2", tournament=tournament_second)

        tournaments = await Tournament.annotate(events_count=Count("events")).filter(
            Q(events_count=1, name="0")
        )
        self.assertEqual(len(tournaments), 1)
        self.assertEqual(tournaments[0].id, tournament.id)

    async def test_filter_by_aggregation_field_with_and_as_two_nodes(self):
        tournament = await Tournament.create(name="0")
        tournament_second = await Tournament.create(name="1")
        await Event.create(name="1", tournament=tournament)
        await Event.create(name="2", tournament=tournament_second)

        tournaments = await Tournament.annotate(events_count=Count("events")).filter(
            Q(events_count=1) & Q(name="0")
        )
        self.assertEqual(len(tournaments), 1)
        self.assertEqual(tournaments[0].id, tournament.id)

    async def test_filter_by_aggregation_field_with_or(self):
        tournament = await Tournament.create(name="0")
        await Tournament.create(name="1")
        await Tournament.create(name="2")
        await Event.create(name="1", tournament=tournament)

        tournaments = await Tournament.annotate(events_count=Count("events")).filter(
            Q(events_count=1) | Q(name="2")
        )
        self.assertEqual(len(tournaments), 2)
        self.assertSetEqual({t.name for t in tournaments}, {"0", "2"})

    async def test_filter_by_aggregation_field_with_or_reversed(self):
        tournament = await Tournament.create(name="0")
        await Tournament.create(name="1")
        await Tournament.create(name="2")
        await Event.create(name="1", tournament=tournament)

        tournaments = await Tournament.annotate(events_count=Count("events")).filter(
            Q(name="2") | Q(events_count=1)
        )
        self.assertEqual(len(tournaments), 2)
        self.assertSetEqual({t.name for t in tournaments}, {"0", "2"})

    async def test_filter_by_aggregation_field_with_or_as_one_node(self):
        tournament = await Tournament.create(name="0")
        await Tournament.create(name="1")
        await Tournament.create(name="2")
        await Event.create(name="1", tournament=tournament)

        tournaments = await Tournament.annotate(events_count=Count("events")).filter(
            Q(events_count=1, name="2", join_type=Q.OR)
        )
        self.assertEqual(len(tournaments), 2)
        self.assertSetEqual({t.name for t in tournaments}, {"0", "2"})

    async def test_filter_by_aggregation_field_with_not(self):
        tournament = await Tournament.create(name="0")
        tournament_second = await Tournament.create(name="1")
        await Event.create(name="1", tournament=tournament)
        await Event.create(name="2", tournament=tournament_second)

        tournaments = await Tournament.annotate(events_count=Count("events")).filter(
            ~Q(events_count=1, name="0")
        )
        self.assertEqual(len(tournaments), 1)
        self.assertEqual(tournaments[0].id, tournament_second.id)

    async def test_filter_by_aggregation_field_with_or_not(self):
        tournament = await Tournament.create(name="0")
        await Tournament.create(name="1")
        await Tournament.create(name="2")
        await Event.create(name="1", tournament=tournament)

        tournaments = await Tournament.annotate(events_count=Count("events")).filter(
            ~(Q(events_count=1) | Q(name="2"))
        )
        self.assertEqual(len(tournaments), 1)
        self.assertSetEqual({t.name for t in tournaments}, {"1"})

    async def test_filter_by_aggregation_field_with_or_not_reversed(self):
        tournament = await Tournament.create(name="0")
        await Tournament.create(name="1")
        await Tournament.create(name="2")
        await Event.create(name="1", tournament=tournament)

        tournaments = await Tournament.annotate(events_count=Count("events")).filter(
            ~(Q(name="2") | Q(events_count=1))
        )
        self.assertEqual(len(tournaments), 1)
        self.assertSetEqual({t.name for t in tournaments}, {"1"})

    async def test_filter_by_aggregation_field_trim(self):
        await Tournament.create(name="  1 ")
        await Tournament.create(name="2  ")

        tournaments = await Tournament.annotate(trimmed_name=Trim("name")).filter(trimmed_name="1")
        self.assertEqual(len(tournaments), 1)
        self.assertSetEqual({(t.name, t.trimmed_name) for t in tournaments}, {("  1 ", "1")})

    async def test_filter_by_aggregation_field_length(self):
        await Tournament.create(name="12345")
        await Tournament.create(name="123")
        await Tournament.create(name="1234")

        tournaments = await Tournament.annotate(name_len=Length("name")).filter(name_len__gte=4)
        self.assertEqual(len(tournaments), 2)
        self.assertSetEqual({t.name for t in tournaments}, {"1234", "12345"})

    async def test_filter_by_aggregation_field_coalesce(self):
        await Tournament.create(name="1", desc="demo")
        await Tournament.create(name="2")

        tournaments = await Tournament.annotate(clean_desc=Coalesce("desc", "demo")).filter(
            clean_desc="demo"
        )
        self.assertEqual(len(tournaments), 2)
        self.assertSetEqual(
            {(t.name, t.clean_desc) for t in tournaments}, {("1", "demo"), ("2", "demo")}
        )

    async def test_filter_by_aggregation_field_coalesce_numeric(self):
        await IntFields.create(intnum=1, intnum_null=10)
        await IntFields.create(intnum=4)

        ints = await IntFields.annotate(clean_intnum_null=Coalesce("intnum_null", 0)).filter(
            clean_intnum_null__in=(0, 10)
        )
        self.assertEqual(len(ints), 2)
        self.assertSetEqual(
            {(i.intnum_null, i.clean_intnum_null) for i in ints}, {(None, 0), (10, 10)}
        )

    async def test_filter_by_aggregation_field_comparison_coalesce_numeric(self):
        await IntFields.create(intnum=3, intnum_null=10)
        await IntFields.create(intnum=1, intnum_null=4)
        await IntFields.create(intnum=2)

        ints = await IntFields.annotate(clean_intnum_null=Coalesce("intnum_null", 0)).filter(
            clean_intnum_null__gt=0
        )
        self.assertEqual(len(ints), 2)
        self.assertSetEqual({i.clean_intnum_null for i in ints}, {10, 4})

    async def test_filter_by_aggregation_field_comparison_length(self):
        t1 = await Tournament.create(name="Tournament")
        await Event.create(name="event1", tournament=t1)
        await Event.create(name="event2", tournament=t1)
        t2 = await Tournament.create(name="contest")
        await Event.create(name="event3", tournament=t2)
        await Tournament.create(name="Championship")
        t4 = await Tournament.create(name="local")
        await Event.create(name="event4", tournament=t4)
        await Event.create(name="event5", tournament=t4)
        tournaments = await Tournament.annotate(
            name_len=Length("name"), event_count=Count("events")
        ).filter(name_len__gt=5, event_count=2)
        self.assertEqual(len(tournaments), 1)
        self.assertSetEqual({t.name for t in tournaments}, {"Tournament"})

    async def test_filter_by_annotation_lower(self):
        await Tournament.create(name="Tournament")
        await Tournament.create(name="NEW Tournament")
        tournaments = await Tournament.annotate(name_lower=Lower("name"))
        self.assertEqual(len(tournaments), 2)
        self.assertSetEqual({t.name_lower for t in tournaments}, {"tournament", "new tournament"})

    async def test_filter_by_annotation_upper(self):
        await Tournament.create(name="ToUrnAmEnT")
        await Tournament.create(name="new TOURnament")
        tournaments = await Tournament.annotate(name_upper=Upper("name"))
        self.assertEqual(len(tournaments), 2)
        self.assertSetEqual({t.name_upper for t in tournaments}, {"TOURNAMENT", "NEW TOURNAMENT"})

    async def test_order_by_annotation(self):
        t1 = await Tournament.create(name="Tournament")
        await Event.create(name="event1", tournament=t1)
        await Event.create(name="event2", tournament=t1)

        res = (
            await Event.filter(tournament=t1).annotate(max_id=Max("event_id")).order_by("-event_id")
        )
        self.assertEqual(len(res), 2)
        self.assertGreater(res[0].event_id, res[1].event_id)
        self.assertEqual(res[0].max_id, res[0].event_id)
        self.assertEqual(res[1].max_id, res[1].event_id)

    async def test_values_select_relation(self):
        with self.assertRaises(ValueError):
            tournament = await Tournament.create(name="New Tournament")
            await Event.create(name="Test", tournament_id=tournament.id)
            await Event.all().values("tournament")

    async def test_values_select_relation_field(self):
        tournament = await Tournament.create(name="New Tournament")
        await Event.create(name="Test", tournament_id=tournament.id)
        event_tournaments = await Event.all().values("tournament__name")
        self.assertEqual(event_tournaments[0]["tournament__name"], tournament.name)

    async def test_values_select_relation_field_name_override(self):
        tournament = await Tournament.create(name="New Tournament")
        await Event.create(name="Test", tournament_id=tournament.id)
        event_tournaments = await Event.all().values(tour="tournament__name")
        self.assertEqual(event_tournaments[0]["tour"], tournament.name)

    async def test_values_list_select_relation_field(self):
        tournament = await Tournament.create(name="New Tournament")
        await Event.create(name="Test", tournament_id=tournament.id)
        event_tournaments = await Event.all().values_list("tournament__name")
        self.assertEqual(event_tournaments[0][0], tournament.name)
