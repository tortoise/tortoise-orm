from tests.testmodels import (
    DefaultOrdered,
    DefaultOrderedDesc,
    DefaultOrderedInvalid,
    Event,
    FKToDefaultOrdered,
    Tournament,
)
from tortoise.contrib import test
from tortoise.exceptions import ConfigurationError, FieldError
from tortoise.functions import Count, Sum


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


class TestDefaultOrdering(test.TestCase):
    async def test_default_order(self):
        await DefaultOrdered.create(one="2", second=1)
        await DefaultOrdered.create(one="1", second=1)

        instance_list = await DefaultOrdered.all()
        self.assertEqual([i.one for i in instance_list], ["1", "2"])

    async def test_default_order_desc(self):
        await DefaultOrderedDesc.create(one="1", second=1)
        await DefaultOrderedDesc.create(one="2", second=1)

        instance_list = await DefaultOrderedDesc.all()
        self.assertEqual([i.one for i in instance_list], ["2", "1"])

    async def test_default_order_invalid(self):
        await DefaultOrderedInvalid.create(one="1", second=1)
        await DefaultOrderedInvalid.create(one="2", second=1)

        with self.assertRaises(ConfigurationError):
            await DefaultOrderedInvalid.all()

    async def test_default_order_annotated_query(self):
        instance = await DefaultOrdered.create(one="2", second=1)
        await FKToDefaultOrdered.create(link=instance, value=10)
        await DefaultOrdered.create(one="1", second=1)

        queryset = DefaultOrdered.all().annotate(res=Sum("related__value"))
        queryset._make_query()
        query = queryset.query.get_sql()
        self.assertTrue("order by" not in query.lower())
