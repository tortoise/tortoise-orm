from tortoise import Tortoise
from tortoise.contrib import test
from tortoise.exceptions import DBConnectionError, TransactionManagementError
from tortoise.tests.testmodels import Tournament
from tortoise.transactions import in_transaction


class TestQueryset(test.IsolatedTestCase):
    @test.requireCapability(daemon=True)
    async def test_reconnect(self):
        await Tournament.create(name="1")

        await Tortoise._connections["models"]._close()

        await Tournament.create(name="2")

        await Tortoise._connections["models"]._close()

        self.assertEqual(
            ["{}:{}".format(a.id, a.name) for a in await Tournament.all()], ["1:1", "2:2"]
        )

    @test.requireCapability(daemon=True)
    async def test_reconnect_fail(self):
        await Tournament.create(name="1")

        await Tortoise._connections["models"]._close()
        realport = Tortoise._connections["models"].port
        Tortoise._connections["models"].port = 1234

        with self.assertRaisesRegex(DBConnectionError, "Failed to reconnect:"):
            await Tournament.create(name="2")

        Tortoise._connections["models"].port = realport

    @test.requireCapability(daemon=True)
    async def test_reconnect_transaction_start(self):
        async with in_transaction():
            await Tournament.create(name="1")

        await Tortoise._connections["models"]._close()

        async with in_transaction():
            await Tournament.create(name="2")

        await Tortoise._connections["models"]._close()

        async with in_transaction():
            self.assertEqual(
                ["{}:{}".format(a.id, a.name) for a in await Tournament.all()], ["1:1", "2:2"]
            )

    @test.requireCapability(daemon=True)
    async def test_reconnect_during_transaction_fails(self):
        await Tournament.create(name="1")

        with self.assertRaises(TransactionManagementError):
            async with in_transaction():
                await Tournament.create(name="2")
                await Tortoise._connections["models"]._close()
                await Tournament.create(name="3")

        self.assertEqual(["{}:{}".format(a.id, a.name) for a in await Tournament.all()], ["1:1"])
