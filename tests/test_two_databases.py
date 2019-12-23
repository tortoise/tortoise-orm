from tests.testmodels import Event, EventTwo, TeamTwo, Tournament
from tortoise import Tortoise
from tortoise.contrib import test
from tortoise.exceptions import OperationalError, ParamsError
from tortoise.transactions import in_transaction


class TestTwoDatabases(test.SimpleTestCase):
    async def setUp(self):
        if Tortoise._inited:
            await self._tearDownDB()
        first_db_config = test.getDBConfig(app_label="models", modules=["tests.testmodels"])
        second_db_config = test.getDBConfig(app_label="events", modules=["tests.testmodels"])
        merged_config = {
            "connections": {**first_db_config["connections"], **second_db_config["connections"]},
            "apps": {**first_db_config["apps"], **second_db_config["apps"]},
        }
        await Tortoise.init(merged_config, _create_db=True)
        await Tortoise.generate_schemas()
        self.db = Tortoise.get_connection("models")
        self.second_db = Tortoise.get_connection("events")

    async def tearDown(self):
        await Tortoise._drop_databases()

    async def test_two_databases(self):
        tournament = await Tournament.create(name="Tournament")
        await EventTwo.create(name="Event", tournament_id=tournament.id)

        with self.assertRaises(OperationalError):
            await self.db.execute_query("SELECT * FROM eventtwo")

        _, results = await self.second_db.execute_query("SELECT * FROM eventtwo")
        self.assertEqual(dict(results[0]), {"id": 1, "name": "Event", "tournament_id": 1})

    async def test_two_databases_relation(self):
        tournament = await Tournament.create(name="Tournament")
        event = await EventTwo.create(name="Event", tournament_id=tournament.id)

        with self.assertRaises(OperationalError):
            await self.db.execute_query("SELECT * FROM eventtwo")

        _, results = await self.second_db.execute_query("SELECT * FROM eventtwo")
        self.assertEqual(dict(results[0]), {"id": 1, "name": "Event", "tournament_id": 1})

        teams = []
        for i in range(2):
            team = await TeamTwo.create(name=f"Team {(i + 1)}")
            teams.append(team)
            await event.participants.add(team)

        self.assertEqual(await TeamTwo.all().order_by("name"), teams)
        self.assertEqual(await event.participants.all().order_by("name"), teams)

        self.assertEqual(
            await TeamTwo.all().order_by("name").values("id", "name"),
            [{"id": 1, "name": "Team 1"}, {"id": 2, "name": "Team 2"}],
        )
        self.assertEqual(
            await event.participants.all().order_by("name").values("id", "name"),
            [{"id": 1, "name": "Team 1"}, {"id": 2, "name": "Team 2"}],
        )

    async def test_two_databases_transactions_switch_db(self):
        async with in_transaction("models"):
            tournament = await Tournament.create(name="Tournament")
            await Event.create(name="Event1", tournament=tournament)
            async with in_transaction("events"):
                event = await EventTwo.create(name="Event2", tournament_id=tournament.id)
                team = await TeamTwo.create(name="Team 1")
                await event.participants.add(team)

        saved_tournament = await Tournament.filter(name="Tournament").first()
        self.assertEqual(tournament.id, saved_tournament.id)
        saved_event = await EventTwo.filter(tournament_id=tournament.id).first()
        self.assertEqual(event.id, saved_event.id)

    async def test_two_databases_transaction_paramerror(self):
        with self.assertRaisesRegex(
            ParamsError,
            "You are running with multiple databases, so you should specify connection_name",
        ):
            async with in_transaction():
                pass
