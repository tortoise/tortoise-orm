import asyncio
import uuid

import asynctest

from tortoise import Tortoise
from tortoise.backends.sqlite.client import SqliteClient
from tortoise.utils import generate_schema


class TestCase(asynctest.TestCase):

    def getDB(self):
        return SqliteClient('/tmp/test-{}.sqlite'.format(uuid.uuid4().hex))

    async def _setUpDB(self):
        self.db = self.getDB()
        await self.db.create_connection()
        if not Tortoise._inited:
            Tortoise.init(self.db)
        else:
            Tortoise._client_routing(self.db)
        await generate_schema(self.db)

    async def _tearDownDB(self):
        await self.db.close()

    def _setUp(self):
        self._init_loop()

        # initialize post-test checks
        test = getattr(self, self._testMethodName)
        checker = getattr(test, asynctest._fail_on._FAIL_ON_ATTR, None)
        self._checker = checker or asynctest._fail_on._fail_on()
        self._checker.before_test(self)

        self.loop.run_until_complete(self._setUpDB())
        if asyncio.iscoroutinefunction(self.setUp):
            self.loop.run_until_complete(self.setUp())
        else:
            self.setUp()

        # don't take into account if the loop ran during setUp
        self.loop._asynctest_ran = False

    def _tearDown(self):
        self.loop.run_until_complete(self._tearDownDB())
        if asyncio.iscoroutinefunction(self.tearDown):
            self.loop.run_until_complete(self.tearDown())
        else:
            self.tearDown()

        # post-test checks
        self._checker.check_test(self)
