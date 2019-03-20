import asyncio

from tortoise.contrib import test
from tortoise.tests.testmodels import Tournament


class TestConcurrencyIsolated(test.IsolatedTestCase):

    async def test_concurrency_read(self):
        await Tournament.create(name='Test')
        tour1 = await Tournament.first()
        all = await asyncio.gather(*[Tournament.first() for _ in range(100)])
        self.assertEqual(all, [tour1 for _ in range(100)])

    async def test_concurrency_create(self):
        all = await asyncio.gather(*[Tournament.create(name='Test') for _ in range(100)])
        all_read = await Tournament.all()
        self.assertEqual(set(all), set(all_read))


class TestConcurrencyTransactioned(test.TestCase):

    async def test_concurrency_read(self):
        await Tournament.create(name='Test')
        tour1 = await Tournament.first()
        all = await asyncio.gather(*[Tournament.first() for _ in range(100)])
        self.assertEqual(all, [tour1 for _ in range(100)])

    async def test_concurrency_create(self):
        all = await asyncio.gather(*[Tournament.create(name='Test') for _ in range(100)])
        all_read = await Tournament.all()
        self.assertEqual(set(all), set(all_read))
