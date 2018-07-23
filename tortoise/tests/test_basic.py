from tortoise.contrib import test
from tortoise.tests.testmodels import Tournament


class TestBasic(test.TestCase):
    async def test_basic(self):
        event = await Tournament.create(name='Test')
        await Tournament.filter(id=event.id).update(name='Updated name')
        saved_event = await Tournament.filter(name='Updated name').first()
        self.assertEqual(saved_event.id, event.id)
        await Tournament(name='Test 2').save()
        self.assertEqual(
            await Tournament.all().values_list('id', flat=True),
            [event.id, event.id + 1]
        )
        self.assertEqual(
            await Tournament.all().values('id', 'name'),
            [{'id': event.id, 'name': 'Updated name'}, {'id': event.id + 1, 'name': 'Test 2'}]
        )
