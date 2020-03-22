from tests.testmodels import Author, Book, Event, Team, Tournament
from tortoise.contrib import test
from tortoise.exceptions import ConfigurationError
from tortoise.functions import Avg, Count, Min, Sum


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

    async def test_group_aggregation(self):
        author = await Author.create(name="Some One")
        await Book.create(name="First!", author=author, rating=4)
        await Book.create(name="Second!", author=author, rating=3)
        await Book.create(name="Third!", author=author, rating=3)

        authors = await Author.all().annotate(average_rating=Avg("books__rating"))
        self.assertAlmostEqual(authors[0].average_rating, 3.3333333333)

        authors = await Author.all().annotate(average_rating=Avg("books__rating")).values()
        self.assertAlmostEqual(authors[0]["average_rating"], 3.3333333333)

        authors = (
            await Author.all()
            .annotate(average_rating=Avg("books__rating"))
            .values("id", "name", "average_rating")
        )
        self.assertAlmostEqual(authors[0]["average_rating"], 3.3333333333)

        authors = await Author.all().annotate(average_rating=Avg("books__rating")).values_list()
        self.assertAlmostEqual(authors[0][2], 3.3333333333)

        authors = (
            await Author.all()
            .annotate(average_rating=Avg("books__rating"))
            .values_list("id", "name", "average_rating")
        )
        self.assertAlmostEqual(authors[0][2], 3.3333333333)
