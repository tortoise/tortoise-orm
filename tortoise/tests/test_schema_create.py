import datetime

import asynctest

from tortoise.contrib.testing import TestCase
from tortoise.tests.testmodels import Event, Team, Tournament


class TestSchemaCreate(TestCase):

    @asynctest.strict
    async def test_schema_create(self):
        tournament = await Tournament.create(name='Test')
        self.assertEquals(tournament.created and tournament.created.date(), datetime.date.today())

        event = await Event.create(name='Test 1', tournament=tournament, prize=100)
        old_time = event.modified
        event.name = 'Test 2'
        await event.save()
        self.assertGreater(event.modified, old_time)
        self.assertEquals(len(event.token), 32)
        await Team.create(name='test')
        result = await Team.all().values('name')
        self.assertEquals(result[0]['name'], 'test')
