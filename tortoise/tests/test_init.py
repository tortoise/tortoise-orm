from tortoise import Tortoise
from tortoise.contrib import test
from tortoise.exceptions import ConfigurationError
from tortoise.tests.testmodels import Tournament


class TestInitErrors(test.SimpleTestCase):
    async def setUp(self):
        self.apps = Tortoise.apps
        self.inited = Tortoise._inited
        Tortoise.apps = {}
        Tortoise._inited = False
        Tortoise._db_routing = None
        Tortoise._global_connection = None
        self.db = await self.getDB()

    async def tearDown(self):
        await self.db.close()
        await self.db.db_delete()
        Tortoise.apps = self.apps
        Tortoise._inited = self.inited

    def test_dup_model(self):
        with self.assertRaisesRegex(ConfigurationError, 'duplicates in'):
            Tortoise.register_model('models', 'Tournament', Tournament)
            Tortoise.register_model('models', 'Tournament', Tournament)

    def test_missing_app_route(self):
        Tortoise.apps = self.apps
        with self.assertRaisesRegex(ConfigurationError, 'No db instanced for apps'):
            Tortoise._client_routing(db_routing={
                'models': self.db,
            })

    def test_exclusive_route_param(self):
        with self.assertRaisesRegex(ConfigurationError, 'You must pass either'):
            Tortoise._client_routing(db_routing={
                'models': self.db,
            }, global_client=self.db)

    def test_not_db(self):
        with self.assertRaisesRegex(ConfigurationError,
                                    'global_client must inherit from BaseDBAsyncClient'):
            Tortoise._client_routing(global_client='moo')

    def test_missing_param(self):
        with self.assertRaisesRegex(ConfigurationError,
                                    'You must pass either global_client or db_routing'):
            Tortoise._client_routing()

    def test_missing_app_route2(self):
        Tortoise.apps = self.apps
        with self.assertRaisesRegex(ConfigurationError,
                                    'All app values must inherit from BaseDBAsyncClient'):
            Tortoise._client_routing(db_routing={
                'models': 'moo',
            })
