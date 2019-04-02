import asyncio

from tortoise.contrib import test
from tortoise.tests.testmodels import Tournament
from tortoise.transactions import in_transaction


class TestConcurrencyIsolated(test.IsolatedTestCase):
    async def test_concurrency_read(self):
        await Tournament.create(name="Test")
        tour1 = await Tournament.first()
        all_read = await asyncio.gather(*[Tournament.first() for _ in range(100)])
        self.assertEqual(all_read, [tour1 for _ in range(100)])

    async def test_concurrency_create(self):
        all_write = await asyncio.gather(
            *[Tournament.create(name="Test") for _ in range(100)]
        )
        all_read = await Tournament.all()
        self.assertEqual(set(all_write), set(all_read))

    async def create_trans_concurrent(self):
        async with in_transaction():
            await asyncio.gather(*[Tournament.create(name="Test") for _ in range(100)])

    @test.expectedFailure
    async def test_concurrency_transactions_create(self):
        await asyncio.gather(*[self.create_trans_concurrent() for _ in range(10)])
        count = await Tournament.all().count()
        self.assertEqual(count, 10000)


class TestConcurrencyTransactioned(test.TestCase):
    async def test_concurrency_read(self):
        await Tournament.create(name="Test")
        tour1 = await Tournament.first()
        all_read = await asyncio.gather(*[Tournament.first() for _ in range(100)])
        self.assertEqual(all_read, [tour1 for _ in range(100)])

    async def test_concurrency_create(self):
        all_write = await asyncio.gather(
            *[Tournament.create(name="Test") for _ in range(100)]
        )
        all_read = await Tournament.all()
        self.assertEqual(set(all_write), set(all_read))
