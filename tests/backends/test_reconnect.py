from tests.testmodels import Tournament
from tortoise import Tortoise
from tortoise.contrib import test
from tortoise.transactions import in_transaction


@test.requireCapability(daemon=True)
class TestReconnect(test.IsolatedTestCase):
    async def test_reconnect(self):
        await Tournament.create(name="1")

        await Tortoise._connections["models"]._expire_connections()

        await Tournament.create(name="2")

        await Tortoise._connections["models"]._expire_connections()

        await Tournament.create(name="3")

        self.assertEqual(
            [f"{a.id}:{a.name}" for a in await Tournament.all()], ["1:1", "2:2", "3:3"]
        )

    @test.requireCapability(supports_transactions=True)
    async def test_reconnect_transaction_start(self):
        async with in_transaction():
            await Tournament.create(name="1")

        await Tortoise._connections["models"]._expire_connections()

        async with in_transaction():
            await Tournament.create(name="2")

        await Tortoise._connections["models"]._expire_connections()

        async with in_transaction():
            self.assertEqual([f"{a.id}:{a.name}" for a in await Tournament.all()], ["1:1", "2:2"])
