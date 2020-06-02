from tortoise import Tortoise
from tortoise.contrib import test
from tortoise.transactions import in_transaction


class TestManualSQL(test.TruncationTestCase):
    async def test_simple_insert(self):
        conn = Tortoise.get_connection("models")
        await conn.execute_query("INSERT INTO author (name) VALUES ('Foo')")
        self.assertEqual(
            await conn.execute_query_dict("SELECT name FROM author"), [{"name": "Foo"}]
        )

    async def test_in_transaction(self):
        async with in_transaction() as conn:
            await conn.execute_query("INSERT INTO author (name) VALUES ('Foo')")

        conn = Tortoise.get_connection("models")
        self.assertEqual(
            await conn.execute_query_dict("SELECT name FROM author"), [{"name": "Foo"}]
        )

    @test.requireCapability(supports_transactions=True)
    async def test_in_transaction_exception(self):
        try:
            async with in_transaction() as conn:
                await conn.execute_query("INSERT INTO author (name) VALUES ('Foo')")
                raise ValueError("oops")
        except ValueError:
            pass

        conn = Tortoise.get_connection("models")
        self.assertEqual(await conn.execute_query_dict("SELECT name FROM author"), [])

    @test.requireCapability(supports_transactions=True)
    async def test_in_transaction_rollback(self):
        async with in_transaction() as conn:
            await conn.execute_query("INSERT INTO author (name) VALUES ('Foo')")
            await conn.rollback()

        conn = Tortoise.get_connection("models")
        self.assertEqual(await conn.execute_query_dict("SELECT name FROM author"), [])

    async def test_in_transaction_commit(self):
        try:
            async with in_transaction() as conn:
                await conn.execute_query("INSERT INTO author (name) VALUES ('Foo')")
                await conn.commit()
                raise ValueError("oops")
        except ValueError:
            pass

        conn = Tortoise.get_connection("models")
        self.assertEqual(
            await conn.execute_query_dict("SELECT name FROM author"), [{"name": "Foo"}]
        )
