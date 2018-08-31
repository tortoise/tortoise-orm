import asyncio as _asyncio
import os as _os
from copy import deepcopy
from typing import List
from unittest import SkipTest, expectedFailure, skip, skipIf, skipUnless  # noqa

from asynctest import TestCase as _TestCase
from asynctest import _fail_on

from tortoise import Tortoise
from tortoise.backends.base.config_generator import generate_config as _generate_config
from tortoise.exceptions import DBConnectionError
from tortoise.transactions import start_transaction

__all__ = ('SimpleTestCase', 'IsolatedTestCase', 'TestCase', 'SkipTest', 'expectedFailure',
           'skip', 'skipIf', 'skipUnless', 'initializer', 'finalizer')
_TORTOISE_TEST_DB = _os.environ.get('TORTOISE_TEST_DB', 'sqlite:///tmp/test-{}.sqlite')

expectedFailure.__doc__ = """
Mark test as expecting failiure.

On success it will be marked as unexpected success.
"""

_CONFIG = {}  # type: dict
_APPS = {}  # type: dict
_CONNECTIONS = {}  # type: dict


def getDBConfig(app_label: str, modules: List[str]) -> dict:
    """
    DB Config factory, for use in testing.
    """
    return _generate_config(
        _TORTOISE_TEST_DB,
        app_modules={
            app_label: modules
        },
        testing=True,
        connection_label=app_label
    )


async def _init_db(config):
    try:
        await Tortoise.init(config)
        await Tortoise._drop_databases()
    except DBConnectionError as exc:  # pragma: nocoverage
        pass

    await Tortoise.init(config, _create_db=True)
    await Tortoise.generate_schemas()


def initializer():
    """
    Sets up the DB for testing. Must be called as part of test environment setup.
    """
    global _CONFIG
    global _APPS
    global _CONNECTIONS
    _CONFIG = getDBConfig(
        app_label='models',
        modules=['tortoise.tests.testmodels'],
    )

    loop = _asyncio.get_event_loop()
    loop.run_until_complete(_init_db(_CONFIG))
    _APPS = deepcopy(Tortoise.apps)
    _CONNECTIONS = Tortoise._connections.copy()
    loop.run_until_complete(Tortoise._reset_connections())


def finalizer():
    """
    Cleans up the DB after testing. Must be called as part of the test environment teardown.
    """
    Tortoise.apps = deepcopy(_APPS)
    Tortoise._connections = _CONNECTIONS.copy()
    loop = _asyncio.get_event_loop()
    loop.run_until_complete(Tortoise._drop_databases())


class SimpleTestCase(_TestCase):
    """
    An asyncio capable test class that provides some helper functions.

    Will run any ``test_*()`` function either as sync or async, depending
    on the signature of the function.
    If you specify ``async test_*()`` then it will run it in an event loop.

    Based on `asynctest <http://asynctest.readthedocs.io/>`_
    """

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


class IsolatedTestCase(SimpleTestCase):
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
        config = getDBConfig(
            app_label='models',
            modules=['tortoise.tests.testmodels'],
        )
        await Tortoise.init(config, _create_db=True)
        await Tortoise.generate_schemas()

    async def _tearDownDB(self) -> None:
        await Tortoise._drop_databases()


class TestCase(SimpleTestCase):
    """
    An asyncio capable test class that will ensure that each test will be run at
    separate transaction that will rollback on finish.
    """

    async def _setUpDB(self):
        Tortoise.apps = deepcopy(_APPS)
        Tortoise._connections = _CONNECTIONS.copy()
        await Tortoise.init(_CONFIG)

        self.transaction = await start_transaction()

    async def _tearDownDB(self) -> None:
        await self.transaction.rollback()
        # Have to reset connections because tests are run in different loops
        await Tortoise._reset_connections()
