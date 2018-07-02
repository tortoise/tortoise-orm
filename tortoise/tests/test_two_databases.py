from sqlite3 import OperationalError

from tortoise import Tortoise
from tortoise.contrib.testing import TestCase
from tortoise.tests.testmodels import EventTwo, TeamTwo, Tournament
from tortoise.utils import generate_schema


class TestTwoDatabases(TestCase):
    async def setUp(self):
        await self._tearDownDB()
        self.db = self.getDB()
        await self.db.create_connection()
        self.second_db = self.getDB()
        await self.second_db.create_connection()
        Tortoise._client_routing(db_routing={
            'models': self.db,
            'events': self.second_db,
        })
        await generate_schema(self.db)
        await generate_schema(self.second_db)

    async def test_two_databases(self):
        tournament = await Tournament.create(name='Tournament')
        await EventTwo.create(name='Event', tournament_id=tournament.id)

        with self.assertRaises(OperationalError):
            await self.db.execute_query('SELECT * FROM "eventtwo"')

        results = await self.second_db.execute_query('SELECT * FROM "eventtwo"')
        self.assertEquals(results, [{'id': 1, 'name': 'Event', 'tournament_id': 1}])

    async def test_two_databases_relation(self):
        tournament = await Tournament.create(name='Tournament')
        event = await EventTwo.create(name='Event', tournament_id=tournament.id)

        with self.assertRaises(OperationalError):
            await self.db.execute_query('SELECT * FROM "eventtwo"')

        results = await self.second_db.execute_query('SELECT * FROM "eventtwo"')
        self.assertEquals(results, [{'id': 1, 'name': 'Event', 'tournament_id': 1}])

        teams = []
        for i in range(2):
            team = await TeamTwo.create(name='Team {}'.format(i + 1))
            teams.append(team)
            await event.participants.add(team)

        self.assertEquals(await TeamTwo.all().order_by('name'), teams)
        self.assertEquals(await event.participants.all().order_by('name'), teams)

        self.assertEquals(
            await TeamTwo.all().order_by('name').values('id', 'name'),
            [{'id': 1, 'name': 'Team 1'}, {'id': 2, 'name': 'Team 2'}]
        )
        self.assertEquals(
            await event.participants.all().order_by('name').values('id', 'name'),
            [{'id': 1, 'name': 'Team 1'}, {'id': 2, 'name': 'Team 2'}]
        )
