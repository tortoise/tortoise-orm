import datetime
import unittest

import asynctest

from tortoise.contrib.testing import TestCase
from tortoise.tests.testmodels import Event, Team, Tournament


class TestSchemaCreate(TestCase):

    @unittest.expectedFailure
    @asynctest.strict
    async def test_schema_create(self):
        tournament = await Tournament.create(name='Test')
        assert tournament.created and tournament.created.date() == datetime.date.today()

        event = await Event.create(name='Test 1', tournament=tournament, prize=100)
        old_time = event.modified
        event.name = 'Test 2'
        await event.save()
        assert event.modified > old_time
        assert len(event.token) == 32
        await Team.create(name='test')
        result = await Team.all().values('name')
        assert result[0]['name'] == 'test'
