import asyncio

from tests.testmodels import Tournament
from tortoise.contrib import test
from tortoise.transactions import in_transaction


class TestConcurrencyIsolated(test.IsolatedTestCase):
    async def test_concurrency_read(self):
        await Tournament.create(name="Test")
        tour1 = await Tournament.first()
        all_read = await asyncio.gather(*[Tournament.first() for _ in range(100)])
        self.assertEqual(all_read, [tour1 for _ in range(100)])

    async def test_concurrency_create(self):
        all_write = await asyncio.gather(*[Tournament.create(name="Test") for _ in range(100)])
        all_read = await Tournament.all()
        self.assertEqual(set(all_write), set(all_read))

    async def create_trans_concurrent(self):
        async with in_transaction():
            await asyncio.gather(*[Tournament.create(name="Test") for _ in range(100)])

    @test.skip("HANGS")
    @test.requireCapability(supports_transactions=True)
    async def test_concurrency_transactions_concurrent(self):
        await asyncio.gather(*[self.create_trans_concurrent() for _ in range(10)])
        count = await Tournament.all().count()
        self.assertEqual(count, 1000)

    async def create_trans(self):
        async with in_transaction():
            await Tournament.create(name="Test")

    @test.requireCapability(supports_transactions=True)
    async def test_concurrency_transactions(self):
        await asyncio.gather(*[self.create_trans() for _ in range(100)])
        count = await Tournament.all().count()
        self.assertEqual(count, 100)


@test.skip("BLOWS UP")
@test.requireCapability(supports_transactions=True)
class TestConcurrencyTransactioned(test.TestCase):
    async def test_concurrency_read(self):
        await Tournament.create(name="Test")
        tour1 = await Tournament.first()
        all_read = await asyncio.gather(*[Tournament.first() for _ in range(100)])
        self.assertEqual(all_read, [tour1 for _ in range(100)])

    async def test_concurrency_create(self):
        all_write = await asyncio.gather(*[Tournament.create(name="Test") for _ in range(100)])
        all_read = await Tournament.all()
        self.assertEqual(set(all_write), set(all_read))
