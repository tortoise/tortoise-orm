from tests.testmodels import Event, Tournament
from tortoise.contrib import test
from tortoise.contrib.test.condition import NotEQ
from tortoise.expressions import F
from tortoise.functions import Length


class TestQueryReuse(test.TestCase):
    async def test_annotations(self):
        a = await Tournament.create(name="A")

        base_query = Tournament.annotate(id_plus_one=F("id") + 1)
        query1 = base_query.annotate(id_plus_two=F("id") + 2)
        query2 = base_query.annotate(id_plus_three=F("id") + 3)
        res = await query1.first()
        self.assertEqual(res.id_plus_one, a.id + 1)
        self.assertEqual(res.id_plus_two, a.id + 2)
        with self.assertRaises(AttributeError):
            getattr(res, "id_plus_three")

        res = await query2.first()
        self.assertEqual(res.id_plus_one, a.id + 1)
        self.assertEqual(res.id_plus_three, a.id + 3)
        with self.assertRaises(AttributeError):
            getattr(res, "id_plus_two")

        res = await query1.first()
        with self.assertRaises(AttributeError):
            getattr(res, "id_plus_three")

    async def test_filters(self):
        a = await Tournament.create(name="A")
        b = await Tournament.create(name="B")
        await Tournament.create(name="C")

        base_query = Tournament.exclude(name="C")
        tournaments = await base_query
        self.assertSetEqual(set(tournaments), {a, b})

        tournaments = await base_query.exclude(name="A")
        self.assertSetEqual(set(tournaments), {b})

        tournaments = await base_query.exclude(name="B")
        self.assertSetEqual(set(tournaments), {a})

    async def test_joins(self):
        tournament_a = await Tournament.create(name="A")
        tournament_b = await Tournament.create(name="B")
        tournament_c = await Tournament.create(name="C")
        event_a = await Event.create(name="A", tournament=tournament_a)
        event_b = await Event.create(name="B", tournament=tournament_b)
        await Event.create(name="C", tournament=tournament_c)

        base_query = Event.exclude(tournament__name="C")
        events = await base_query
        self.assertSetEqual(set(events), {event_a, event_b})

        events = await base_query.exclude(name="A")
        self.assertSetEqual(set(events), {event_b})

        events = await base_query.exclude(name="B")
        self.assertSetEqual(set(events), {event_a})

    async def test_order_by(self):
        a = await Tournament.create(name="A")
        b = await Tournament.create(name="B")

        base_query = Tournament.all().order_by("name")
        tournaments = await base_query
        self.assertEqual(tournaments, [a, b])

        tournaments = await base_query.order_by("-name")
        self.assertEqual(tournaments, [b, a])

    @test.requireCapability(dialect=NotEQ("mssql"))
    async def test_values_with_annotations(self):
        await Tournament.create(name="Championship")
        await Tournament.create(name="Super Bowl")

        base_query = Tournament.annotate(name_length=Length("name"))
        tournaments = await base_query.values_list("name")
        self.assertListSortEqual(tournaments, [("Championship",), ("Super Bowl",)])

        tournaments = await base_query.values_list("name_length")
        self.assertListSortEqual(tournaments, [(10,), (12,)])
