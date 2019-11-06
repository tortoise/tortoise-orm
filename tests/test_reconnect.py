from tests.testmodels import Tournament
from tortoise import Tortoise
from tortoise.contrib import test
from tortoise.exceptions import DBConnectionError, TransactionManagementError
from tortoise.transactions import in_transaction


@test.requireCapability(daemon=True)
class TestQueryset(test.IsolatedTestCase):
    async def test_reconnect(self):
        await Tournament.create(name="1")

        await Tortoise._connections["models"]._close()
        await Tortoise._connections["models"].create_connection(with_db=True)

        await Tournament.create(name="2")

        await Tortoise._connections["models"]._close()
        await Tortoise._connections["models"].create_connection(with_db=True)

        self.assertEqual([f"{a.id}:{a.name}" for a in await Tournament.all()], ["1:1", "2:2"])

    @test.skip("closes the pool, needs a better way to simulate failures")
    async def test_reconnect_fail(self):
        await Tournament.create(name="1")

        await Tortoise._connections["models"]._close()
        realport = Tortoise._connections["models"].port
        Tortoise._connections["models"].port = 1234

        with self.assertRaisesRegex(DBConnectionError, "Failed to reconnect:"):
            await Tournament.create(name="2")

        Tortoise._connections["models"].port = realport

    @test.requireCapability(supports_transactions=True)
    async def test_reconnect_transaction_start(self):
        async with in_transaction():
            await Tournament.create(name="1")

        await Tortoise._connections["models"]._close()
        await Tortoise._connections["models"].create_connection(with_db=True)

        async with in_transaction():
            await Tournament.create(name="2")

        await Tortoise._connections["models"]._close()
        await Tortoise._connections["models"].create_connection(with_db=True)

        async with in_transaction():
            self.assertEqual([f"{a.id}:{a.name}" for a in await Tournament.all()], ["1:1", "2:2"])

    @test.skip(
        "you can't just open a new pool and expect to be able to release the old connection to it"
    )
    @test.requireCapability(supports_transactions=True)
    async def test_reconnect_during_transaction_fails(self):
        await Tournament.create(name="1")

        with self.assertRaises(TransactionManagementError):
            async with in_transaction():
                await Tournament.create(name="2")
                await Tortoise._connections["models"]._close()
                await Tournament.create(name="3")

        self.assertEqual([f"{a.id}:{a.name}" for a in await Tournament.all()], ["1:1"])
