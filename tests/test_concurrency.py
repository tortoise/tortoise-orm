import asyncio
import sys

from tests.testmodels import Tournament, UniqueName
from tortoise import Tortoise, connections
from tortoise.contrib import test
from tortoise.contrib.test.condition import NotEQ
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

    async def test_nonconcurrent_get_or_create(self):
        unas = [await UniqueName.get_or_create(name="c") for _ in range(10)]
        una_created = [una[1] for una in unas if una[1] is True]
        self.assertEqual(len(una_created), 1)
        for una in unas:
            self.assertEqual(una[0], unas[0][0])

    @test.skipIf(sys.version_info < (3, 7), "aiocontextvars backport not handling this well")
    @test.requireCapability(dialect=NotEQ("mssql"))
    async def test_concurrent_get_or_create(self):
        unas = await asyncio.gather(*[UniqueName.get_or_create(name="d") for _ in range(10)])
        una_created = [una[1] for una in unas if una[1] is True]
        self.assertEqual(len(una_created), 1)
        for una in unas:
            self.assertEqual(una[0], unas[0][0])

    @test.skipIf(sys.version_info < (3, 7), "aiocontextvars backport not handling this well")
    @test.requireCapability(supports_transactions=True)
    async def test_concurrent_transactions_with_multiple_ops(self):
        async def create_in_transaction():
            async with in_transaction():
                await asyncio.gather(*[Tournament.create(name="Test") for _ in range(100)])

        await asyncio.gather(*[create_in_transaction() for _ in range(10)])
        count = await Tournament.all().count()
        self.assertEqual(count, 1000)

    @test.skipIf(sys.version_info < (3, 7), "aiocontextvars backport not handling this well")
    @test.requireCapability(supports_transactions=True)
    async def test_concurrent_transactions_with_single_op(self):
        async def create():
            async with in_transaction():
                await Tournament.create(name="Test")

        await asyncio.gather(*[create() for _ in range(100)])
        count = await Tournament.all().count()
        self.assertEqual(count, 100)

    @test.skipIf(sys.version_info < (3, 7), "aiocontextvars backport not handling this well")
    @test.requireCapability(supports_transactions=True)
    async def test_nested_concurrent_transactions_with_multiple_ops(self):
        async def create_in_transaction():
            async with in_transaction():
                async with in_transaction():
                    await asyncio.gather(*[Tournament.create(name="Test") for _ in range(100)])

        await asyncio.gather(*[create_in_transaction() for _ in range(10)])
        count = await Tournament.all().count()
        self.assertEqual(count, 1000)


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


class TestConcurrentDBConnectionInitialization(test.IsolatedTestCase):
    """Tortoise.init is lazy and does not initialize the database connection until the first query.
    These tests ensure that concurrent queries do not cause initialization issues."""

    async def _setUpDB(self) -> None:
        """Override to avoid database connection initialization when generating the schema."""
        await super()._setUpDB()
        config = test.getDBConfig(app_label="models", modules=test._MODULES)
        await Tortoise.init(config, _create_db=True)

    async def test_concurrent_queries(self):
        await asyncio.gather(
            *[connections.get("models").execute_query("SELECT 1") for _ in range(100)]
        )

    async def test_concurrent_transactions(self) -> None:
        async def transaction() -> None:
            async with in_transaction():
                await connections.get("models").execute_query("SELECT 1")

        await asyncio.gather(*[transaction() for _ in range(100)])
