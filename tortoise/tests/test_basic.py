import asynctest

from tortoise.contrib.testing import TestCase
from tortoise.tests.testmodels import Tournament


class TestBasic(TestCase):
    @asynctest.strict
    async def test_basic(self):
        event = await Tournament.create(name='Test')
        await Tournament.filter(id=event.id).update(name='Updated name')
        saved_event = await Tournament.filter(name='Updated name').first()
        assert saved_event.id == event.id
        await Tournament(name='Test 2').save()
        await Tournament.all().values_list('id', flat=True)
        await Tournament.all().values('id', 'name')
