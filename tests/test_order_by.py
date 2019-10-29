from tests.testmodels import Event, Tournament
from tortoise.contrib import test
from tortoise.exceptions import FieldError
from tortoise.functions import Count


class TestOrderBy(test.TestCase):
    async def test_order_by(self):
        await Tournament.create(name="1")
        await Tournament.create(name="2")

        tournaments = await Tournament.all().order_by("name")
        self.assertEqual([t.name for t in tournaments], ["1", "2"])

    async def test_order_by_reversed(self):
        await Tournament.create(name="1")
        await Tournament.create(name="2")

        tournaments = await Tournament.all().order_by("-name")
        self.assertEqual([t.name for t in tournaments], ["2", "1"])

    async def test_order_by_related(self):
        tournament_first = await Tournament.create(name="1")
        tournament_second = await Tournament.create(name="2")
        await Event.create(name="b", tournament=tournament_first)
        await Event.create(name="a", tournament=tournament_second)

        tournaments = await Tournament.all().order_by("events__name")
        self.assertEqual([t.name for t in tournaments], ["2", "1"])

    async def test_order_by_related_reversed(self):
        tournament_first = await Tournament.create(name="1")
        tournament_second = await Tournament.create(name="2")
        await Event.create(name="b", tournament=tournament_first)
        await Event.create(name="a", tournament=tournament_second)

        tournaments = await Tournament.all().order_by("-events__name")
        self.assertEqual([t.name for t in tournaments], ["1", "2"])

    async def test_order_by_relation(self):
        with self.assertRaises(FieldError):
            tournament_first = await Tournament.create(name="1")
            await Event.create(name="b", tournament=tournament_first)

            await Tournament.all().order_by("events")

    async def test_order_by_unknown_field(self):
        with self.assertRaises(FieldError):
            tournament_first = await Tournament.create(name="1")
            await Event.create(name="b", tournament=tournament_first)

            await Tournament.all().order_by("something_else")

    async def test_order_by_aggregation(self):
        tournament_first = await Tournament.create(name="1")
        tournament_second = await Tournament.create(name="2")
        await Event.create(name="b", tournament=tournament_first)
        await Event.create(name="c", tournament=tournament_first)
        await Event.create(name="a", tournament=tournament_second)

        tournaments = await Tournament.annotate(events_count=Count("events")).order_by(
            "events_count"
        )
        self.assertEqual([t.name for t in tournaments], ["2", "1"])

    async def test_order_by_aggregation_reversed(self):
        tournament_first = await Tournament.create(name="1")
        tournament_second = await Tournament.create(name="2")
        await Event.create(name="b", tournament=tournament_first)
        await Event.create(name="c", tournament=tournament_first)
        await Event.create(name="a", tournament=tournament_second)

        tournaments = await Tournament.annotate(events_count=Count("events")).order_by(
            "-events_count"
        )
        self.assertEqual([t.name for t in tournaments], ["1", "2"])
