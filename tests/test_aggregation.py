from tests.testmodels import Event, MinRelation, Team, Tournament
from tortoise.contrib import test
from tortoise.exceptions import ConfigurationError
from tortoise.functions import Count, Min, Sum
from tortoise.query_utils import Q


class TestAggregation(test.TestCase):
    async def test_aggregation(self):
        tournament = Tournament(name="New Tournament")
        await tournament.save()
        await Tournament.create(name="Second tournament")
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

        tournaments_with_count = (
            await Tournament.all()
            .annotate(events_count=Count("events"))
            .filter(events_count__gte=1)
        )
        self.assertEqual(len(tournaments_with_count), 1)
        self.assertEqual(tournaments_with_count[0].events_count, 2)

        event_with_lowest_team_id = (
            await Event.filter(event_id=event.event_id)
            .first()
            .annotate(lowest_team_id=Min("participants__id"))
        )
        self.assertEqual(event_with_lowest_team_id.lowest_team_id, participants[0].id)

        ordered_tournaments = (
            await Tournament.all().annotate(events_count=Count("events")).order_by("events_count")
        )
        self.assertEqual(len(ordered_tournaments), 2)
        self.assertEqual(ordered_tournaments[1].id, tournament.id)
        event_with_annotation = (
            await Event.all().annotate(tournament_test_id=Sum("tournament__id")).first()
        )
        self.assertEqual(
            event_with_annotation.tournament_test_id, event_with_annotation.tournament_id
        )

        with self.assertRaisesRegex(ConfigurationError, "name__id not resolvable"):
            await Event.all().annotate(tournament_test_id=Sum("name__id")).first()

    async def test_aggregation_with_distinct(self):
        tournament = await Tournament.create(name="New Tournament")
        await Event.create(name="Event 1", tournament=tournament)
        await Event.create(name="Event 2", tournament=tournament)
        await MinRelation.create(tournament=tournament)

        tournament_2 = await Tournament.create(name="New Tournament")
        await Event.create(name="Event 1", tournament=tournament_2)
        await Event.create(name="Event 2", tournament=tournament_2)
        await Event.create(name="Event 3", tournament=tournament_2)
        await MinRelation.create(tournament=tournament_2)
        await MinRelation.create(tournament=tournament_2)

        school_with_distinct_count = (
            await Tournament.filter(id=tournament_2.id)
            .annotate(
                events_count=Count("events", distinct=True),
                minrelations_count=Count("minrelations", distinct=True),
            )
            .first()
        )

        self.assertEqual(school_with_distinct_count.events_count, 3)
        self.assertEqual(school_with_distinct_count.minrelations_count, 2)

    async def test_aggregation_with_filter(self):
        tournament = await Tournament.create(name="New Tournament")
        await Event.create(name="Event 1", tournament=tournament)
        await Event.create(name="Event 2", tournament=tournament)
        await Event.create(name="Event 3", tournament=tournament)
        await MinRelation.create(tournament=tournament)
        await MinRelation.create(tournament=tournament)

        tournament_with_filter = (
            await Tournament.all()
            .annotate(
                all=Count("events", _filter=Q(name__in=["New Tournament"])),
                no=Count("events", _filter=Q(name__not="New Tournament")),
                event1=Count("events", _filter=Q(events__name="Event 1")),
                not_event1=Count("events", _filter=Q(events__name__not="Event 1")),
            )
            .first()
        )

        self.assertEqual(tournament_with_filter.all, 3)
        self.assertEqual(tournament_with_filter.no, 0)
        self.assertEqual(tournament_with_filter.event1, 1)
        self.assertEqual(tournament_with_filter.not_event1, 2)
