import asyncio as _asyncio
import os as _os
from unittest import SkipTest, expectedFailure, skip, skipIf, skipUnless  # noqa

from asynctest import TestCase as _TestCase
from asynctest import _fail_on

from tortoise import Tortoise as _Tortoise
from tortoise.backends.base.client import BaseDBAsyncClient as _BaseDBAsyncClient
from tortoise.backends.base.db_url import expand_db_url as _expand_db_url
from tortoise.utils import generate_schema as _generate_schema

__all__ = ('SimpleTestCase', 'TransactionTestCase', 'TestCase', 'SkipTest', 'expectedFailure',
           'skip', 'skipIf', 'skipUnless')
_TORTOISE_TEST_DB = _os.environ.get('TORTOISE_TEST_DB', 'sqlite:///tmp/test-{}.sqlite')

expectedFailure.__doc__ = """
Mark test as expecting failiure.

On success it will be marked as unexpected success.
"""


class SimpleTestCase(_TestCase):
    """
    An asyncio capable test class that provides some helper functions.

    Will run any ``test_*()`` function either as sync or async, depending
    on the signature of the function.
    If you specify ``async test_*()`` then it will run it in an event loop.

    Based on `asynctest <http://asynctest.readthedocs.io/>`_
    """

    async def getDB(self) -> _BaseDBAsyncClient:
        """
        DB Client factory, for use in testing.

        Please remember to call ``.close()`` and then ``.delete()`` on the returned object.
        """
        dbconf = _expand_db_url(_TORTOISE_TEST_DB, testing=True)
        db = dbconf['client'](**dbconf['params'])
        await db.db_create()
        await db.create_connection()

        return db

    async def _setUpDB(self):
        pass

    async def _tearDownDB(self) -> None:
        pass

    def _setUp(self) -> None:
        self._init_loop()

        # initialize post-test checks
        test = getattr(self, self._testMethodName)
        checker = getattr(test, _fail_on._FAIL_ON_ATTR, None)
        self._checker = checker or _fail_on._fail_on()
        self._checker.before_test(self)

        self.loop.run_until_complete(self._setUpDB())
        if _asyncio.iscoroutinefunction(self.setUp):
            self.loop.run_until_complete(self.setUp())
        else:
            self.setUp()

        # don't take into account if the loop ran during setUp
        self.loop._asynctest_ran = False

    def _tearDown(self) -> None:
        self.loop.run_until_complete(self._tearDownDB())
        if _asyncio.iscoroutinefunction(self.tearDown):
            self.loop.run_until_complete(self.tearDown())
        else:
            self.tearDown()

        # post-test checks
        self._checker.check_test(self)


class TransactionTestCase(SimpleTestCase):
    """
    An asyncio capable test class that will ensure that an isolated test db
    is available for each test.

    It will create and destroy a new DB instance for every test.
    This is obviously slow, but guarantees a fresh DB.

    It will define a ``self.db`` which is the fully initialised (with DB schema)
    DB Client object.
    """
    # pylint: disable=C0103,W0201

    async def _setUpDB(self):
        self.db = await self.getDB()
        if not _Tortoise._inited:
            _Tortoise.init(self.db)
        else:
            _Tortoise._client_routing(self.db)
        await _generate_schema(self.db)

    async def _tearDownDB(self) -> None:
        await self.db.close()
        await self.db.db_delete()


class TestCase(TransactionTestCase):
    """
    An asyncio capable test class that will ensure that an partially isolated test db
    is available for each test.

    It will wrap each test in a transaction and roll the DB back.
    This is much faster, but requires that your test does not explicitly use transactions.

    .. note::
        Currently does not run any faster than ``TransactionTestCase``, will be sped up later on.
    """
    # TODO: Make this wrap everything in a rollback-transaction instead
    pass
