import datetime

from tortoise.contrib import test
from tortoise.tests.testmodels import Event, Team, Tournament


class TestSchemaCreate(test.TestCase):

    async def test_schema_create(self):
        tournament = await Tournament.create(name='Test')
        self.assertEqual(
            tournament.created and tournament.created.date(),
            datetime.datetime.utcnow().date()
        )

        event = await Event.create(name='Test 1', tournament=tournament, prize=100)
        old_time = event.modified
        event.name = 'Test 2'
        await event.save()
        self.assertGreater(event.modified, old_time)
        self.assertEqual(len(event.token), 32)
        await Team.create(name='test')
        result = await Team.all().values('name')
        self.assertEqual(result[0]['name'], 'test')
