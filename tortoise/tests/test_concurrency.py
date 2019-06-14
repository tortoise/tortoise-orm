import asyncio
from unittest import skip

from tortoise.contrib import test
from tortoise.contrib.test import requireCapability
from tortoise.tests.testmodels import Tournament, UniqueTournament
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
            #  This test is bound to fail because creating new tasks
            #  creates them with empty context, so ContextVars are reset to default value
            await asyncio.gather(*[Tournament.create(name="Test") for _ in range(100)])

    @skip("never successful")
    @test.expectedFailure
    async def test_concurrency_transactions_create(self):
        await asyncio.gather(*[self.create_trans_concurrent() for _ in range(11)])
        count = await Tournament.all().count()
        self.assertEqual(count, 1100)

    async def create_trans_concurrent_explicit(self):
        async with in_transaction() as tr:
            await asyncio.gather(*[Tournament.create(name="Test", using_db=tr) for _ in range(100)])

    @requireCapability(pooling=True)
    async def test_concurrency_transactions_create_explicit(self):
        await asyncio.gather(*[self.create_trans_concurrent_explicit() for _ in range(11)])
        count = await Tournament.all().count()
        self.assertEqual(count, 1100)

    async def test_get_or_create_concurrent(self):
        tasks = [
            UniqueTournament.get_or_create(name="Test"),
            UniqueTournament.get_or_create(name="Test"),
        ]
        res1, res2 = await asyncio.gather(*tasks)
        self.assertNotEqual(res1[1], res2[1])
        self.assertEqual(res2[0].pk, res2[0].pk)


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
