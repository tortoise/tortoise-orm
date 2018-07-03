import asyncio
import os

import asynctest

from tortoise import Tortoise
from tortoise.backends.base.client import BaseDBAsyncClient
from tortoise.backends.base.db_url import expand_db_url
from tortoise.utils import generate_schema

TORTOISE_TEST_DB = os.environ.get('TORTOISE_TEST_DB', 'sqlite:///tmp/test-{}.sqlite')


class TestCase(asynctest.TestCase):
    """
    An asyncio capable TestCase that will ensure that an isolated test db
      is available for each test.

    Based on ``asynctest``.
    """
    # pylint: disable=C0103,W0201

    async def getDB(self) -> BaseDBAsyncClient:
        dbconf = expand_db_url(TORTOISE_TEST_DB, testing=True)
        db = dbconf['client'](**dbconf['params'])
        await db.db_create()
        await db.create_connection()

        return db

    async def _setUpDB(self):
        self.db = await self.getDB()
        if not Tortoise._inited:
            Tortoise.init(self.db)
        else:
            Tortoise._client_routing(self.db)
        await generate_schema(self.db)

    async def _tearDownDB(self) -> None:
        await self.db.close()
        await self.db.db_delete()

    def _setUp(self) -> None:
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

    def _tearDown(self) -> None:
        self.loop.run_until_complete(self._tearDownDB())
        if asyncio.iscoroutinefunction(self.tearDown):
            self.loop.run_until_complete(self.tearDown())
        else:
            self.tearDown()

        # post-test checks
        self._checker.check_test(self)
