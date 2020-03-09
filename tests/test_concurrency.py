import asyncio
import sys

from tests.testmodels import Tournament, UniqueName
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

    async def test_nonconcurrent_get_or_create(self):
        unas = [await UniqueName.get_or_create(name="c") for _ in range(10)]
        una_created = [una[1] for una in unas if una[1] is True]
        self.assertEqual(len(una_created), 1)
        for una in unas:
            self.assertEqual(una[0], unas[0][0])

    @test.skipIf(sys.version_info < (3, 7), "aiocontextvars backport not handling this well")
    async def test_concurrent_get_or_create(self):
        unas = await asyncio.gather(*[UniqueName.get_or_create(name="d") for _ in range(10)])
        una_created = [una[1] for una in unas if una[1] is True]
        self.assertEqual(len(una_created), 1)
        for una in unas:
            self.assertEqual(una[0], unas[0][0])

    @test.skipIf(sys.version_info < (3, 7), "aiocontextvars backport not handling this well")
    @test.requireCapability(supports_transactions=True)
    async def test_concurrency_transactions_concurrent(self):
        await asyncio.gather(*[self.create_trans_concurrent() for _ in range(10)])
        count = await Tournament.all().count()
        self.assertEqual(count, 1000)

    async def create_trans(self):
        async with in_transaction():
            await Tournament.create(name="Test")

    @test.skipIf(sys.version_info < (3, 7), "aiocontextvars backport not handling this well")
    @test.requireCapability(supports_transactions=True)
    async def test_concurrency_transactions(self):
        await asyncio.gather(*[self.create_trans() for _ in range(100)])
        count = await Tournament.all().count()
        self.assertEqual(count, 100)


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

    async def test_nonconcurrent_get_or_create(self):
        unas = [await UniqueName.get_or_create(name="a") for _ in range(10)]
        una_created = [una[1] for una in unas if una[1] is True]
        self.assertEqual(len(una_created), 1)
        for una in unas:
            self.assertEqual(una[0], unas[0][0])

    @test.skipIf(sys.version_info < (3, 7), "aiocontextvars backport not handling this well")
    async def test_concurrent_get_or_create(self):
        unas = await asyncio.gather(*[UniqueName.get_or_create(name="b") for _ in range(10)])
        una_created = [una[1] for una in unas if una[1] is True]
        self.assertEqual(len(una_created), 1)
        for una in unas:
            self.assertEqual(una[0], unas[0][0])
