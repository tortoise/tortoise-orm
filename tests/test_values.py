from pypika import CustomFunction

from tests.testmodels import Event, Team, Tournament
from tortoise.contrib import test
from tortoise.contrib.test.condition import In, NotEQ
from tortoise.exceptions import FieldError
from tortoise.expressions import Function
from tortoise.functions import Length, Trim


class TestValues(test.TestCase):
    async def test_values_related_fk(self):
        tournament = await Tournament.create(name="New Tournament")
        await Event.create(name="Test", tournament_id=tournament.id)

        event2 = await Event.filter(name="Test").values("name", "tournament__name")
        self.assertEqual(event2[0], {"name": "Test", "tournament__name": "New Tournament"})

    async def test_values_list_related_fk(self):
        tournament = await Tournament.create(name="New Tournament")
        await Event.create(name="Test", tournament_id=tournament.id)

        event2 = await Event.filter(name="Test").values_list("name", "tournament__name")
        self.assertEqual(event2[0], ("Test", "New Tournament"))

    async def test_values_related_rfk(self):
        tournament = await Tournament.create(name="New Tournament")
        await Event.create(name="Test", tournament_id=tournament.id)

        tournament2 = await Tournament.filter(name="New Tournament").values("name", "events__name")
        self.assertEqual(tournament2[0], {"name": "New Tournament", "events__name": "Test"})

    async def test_values_related_rfk_reuse_query(self):
        tournament = await Tournament.create(name="New Tournament")
        await Event.create(name="Test", tournament_id=tournament.id)

        query = Tournament.filter(name="New Tournament").values("name", "events__name")
        tournament2 = await query
        self.assertEqual(tournament2[0], {"name": "New Tournament", "events__name": "Test"})

        tournament2 = await query
        self.assertEqual(tournament2[0], {"name": "New Tournament", "events__name": "Test"})

    async def test_values_list_related_rfk(self):
        tournament = await Tournament.create(name="New Tournament")
        await Event.create(name="Test", tournament_id=tournament.id)

        tournament2 = await Tournament.filter(name="New Tournament").values_list(
            "name", "events__name"
        )
        self.assertEqual(tournament2[0], ("New Tournament", "Test"))

    async def test_values_list_related_rfk_reuse_query(self):
        tournament = await Tournament.create(name="New Tournament")
        await Event.create(name="Test", tournament_id=tournament.id)

        query = Tournament.filter(name="New Tournament").values_list("name", "events__name")
        tournament2 = await query
        self.assertEqual(tournament2[0], ("New Tournament", "Test"))

        tournament2 = await query
        self.assertEqual(tournament2[0], ("New Tournament", "Test"))

    async def test_values_related_m2m(self):
        tournament = await Tournament.create(name="New Tournament")
        event = await Event.create(name="Test", tournament_id=tournament.id)
        team = await Team.create(name="Some Team")
        await event.participants.add(team)

        tournament2 = await Event.filter(name="Test").values("name", "participants__name")
        self.assertEqual(tournament2[0], {"name": "Test", "participants__name": "Some Team"})

    async def test_values_list_related_m2m(self):
        tournament = await Tournament.create(name="New Tournament")
        event = await Event.create(name="Test", tournament_id=tournament.id)
        team = await Team.create(name="Some Team")
        await event.participants.add(team)

        tournament2 = await Event.filter(name="Test").values_list("name", "participants__name")
        self.assertEqual(tournament2[0], ("Test", "Some Team"))

    async def test_values_related_fk_itself(self):
        tournament = await Tournament.create(name="New Tournament")
        await Event.create(name="Test", tournament_id=tournament.id)

        with self.assertRaisesRegex(ValueError, 'Selecting relation "tournament" is not possible'):
            await Event.filter(name="Test").values("name", "tournament")

    async def test_values_list_related_fk_itself(self):
        tournament = await Tournament.create(name="New Tournament")
        await Event.create(name="Test", tournament_id=tournament.id)

        with self.assertRaisesRegex(ValueError, 'Selecting relation "tournament" is not possible'):
            await Event.filter(name="Test").values_list("name", "tournament")

    async def test_values_related_rfk_itself(self):
        tournament = await Tournament.create(name="New Tournament")
        await Event.create(name="Test", tournament_id=tournament.id)

        with self.assertRaisesRegex(ValueError, 'Selecting relation "events" is not possible'):
            await Tournament.filter(name="New Tournament").values("name", "events")

    async def test_values_list_related_rfk_itself(self):
        tournament = await Tournament.create(name="New Tournament")
        await Event.create(name="Test", tournament_id=tournament.id)

        with self.assertRaisesRegex(ValueError, 'Selecting relation "events" is not possible'):
            await Tournament.filter(name="New Tournament").values_list("name", "events")

    async def test_values_related_m2m_itself(self):
        tournament = await Tournament.create(name="New Tournament")
        event = await Event.create(name="Test", tournament_id=tournament.id)
        team = await Team.create(name="Some Team")
        await event.participants.add(team)

        with self.assertRaisesRegex(
            ValueError, 'Selecting relation "participants" is not possible'
        ):
            await Event.filter(name="Test").values("name", "participants")

    async def test_values_list_related_m2m_itself(self):
        tournament = await Tournament.create(name="New Tournament")
        event = await Event.create(name="Test", tournament_id=tournament.id)
        team = await Team.create(name="Some Team")
        await event.participants.add(team)

        with self.assertRaisesRegex(
            ValueError, 'Selecting relation "participants" is not possible'
        ):
            await Event.filter(name="Test").values_list("name", "participants")

    async def test_values_bad_key(self):
        tournament = await Tournament.create(name="New Tournament")
        await Event.create(name="Test", tournament_id=tournament.id)

        with self.assertRaisesRegex(FieldError, 'Unknown field "neem" for model "Event"'):
            await Event.filter(name="Test").values("name", "neem")

    async def test_values_list_bad_key(self):
        tournament = await Tournament.create(name="New Tournament")
        await Event.create(name="Test", tournament_id=tournament.id)

        with self.assertRaisesRegex(FieldError, 'Unknown field "neem" for model "Event"'):
            await Event.filter(name="Test").values_list("name", "neem")

    async def test_values_related_bad_key(self):
        tournament = await Tournament.create(name="New Tournament")
        await Event.create(name="Test", tournament_id=tournament.id)

        with self.assertRaisesRegex(FieldError, 'Unknown field "neem" for model "Tournament"'):
            await Event.filter(name="Test").values("name", "tournament__neem")

    async def test_values_list_related_bad_key(self):
        tournament = await Tournament.create(name="New Tournament")
        await Event.create(name="Test", tournament_id=tournament.id)

        with self.assertRaisesRegex(FieldError, 'Unknown field "neem" for model "Tournament"'):
            await Event.filter(name="Test").values_list("name", "tournament__neem")

    @test.requireCapability(dialect="!mssql")
    async def test_values_list_annotations_length(self):
        await Tournament.create(name="Championship")
        await Tournament.create(name="Super Bowl")

        tournaments = await Tournament.annotate(name_length=Length("name")).values_list(
            "name", "name_length"
        )
        self.assertListSortEqual(tournaments, [("Championship", 12), ("Super Bowl", 10)])

    @test.requireCapability(dialect=NotEQ("mssql"))
    async def test_values_annotations_length(self):
        await Tournament.create(name="Championship")
        await Tournament.create(name="Super Bowl")

        tournaments = await Tournament.annotate(name_slength=Length("name")).values(
            "name", "name_slength"
        )
        self.assertListSortEqual(
            tournaments,
            [
                {"name": "Championship", "name_slength": 12},
                {"name": "Super Bowl", "name_slength": 10},
            ],
            sorted_key="name",
        )

    async def test_values_list_annotations_trim(self):
        await Tournament.create(name="  x")
        await Tournament.create(name=" y ")

        tournaments = await Tournament.annotate(name_trim=Trim("name")).values_list(
            "name", "name_trim"
        )
        self.assertListSortEqual(tournaments, [("  x", "x"), (" y ", "y")])

    async def test_values_annotations_trim(self):
        await Tournament.create(name="  x")
        await Tournament.create(name=" y ")

        tournaments = await Tournament.annotate(name_trim=Trim("name")).values("name", "name_trim")
        self.assertListSortEqual(
            tournaments,
            [{"name": "  x", "name_trim": "x"}, {"name": " y ", "name_trim": "y"}],
            sorted_key="name",
        )

    @test.requireCapability(dialect=In("sqlite"))
    async def test_values_with_custom_function(self):
        class TruncMonth(Function):
            database_func = CustomFunction("DATE_FORMAT", ["name", "dt_format"])

        sql = Tournament.all().annotate(date=TruncMonth("created", "%Y-%m-%d")).values("date").sql()
        self.assertEqual(
            sql,
            'SELECT DATE_FORMAT("created",?) "date" FROM "tournament"',
        )
