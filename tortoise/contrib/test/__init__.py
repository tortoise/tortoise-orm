import asyncio
import os as _os
from asyncio.selector_events import BaseSelectorEventLoop
from functools import wraps
from typing import Any, List, Optional
from unittest import SkipTest, expectedFailure, skip, skipIf, skipUnless  # noqa

from asynctest import TestCase as _TestCase
from asynctest import _fail_on
from asynctest.case import _Policy

from tortoise import Tortoise
from tortoise.backends.base.config_generator import generate_config as _generate_config
from tortoise.exceptions import DBConnectionError
from tortoise.transactions import current_transaction_map, start_transaction

__all__ = (
    "SimpleTestCase",
    "IsolatedTestCase",
    "TestCase",
    "SkipTest",
    "expectedFailure",
    "skip",
    "skipIf",
    "skipUnless",
    "env_initializer",
    "initializer",
    "finalizer",
    "getDBConfig",
    "requireCapability",
)
_TORTOISE_TEST_DB = "sqlite://:memory:"

expectedFailure.__doc__ = """
Mark test as expecting failiure.

On success it will be marked as unexpected success.
"""

_CONFIG = {}  # type: dict
_CONNECTIONS = {}  # type: dict
_SELECTOR = None
_LOOP = None  # type: BaseSelectorEventLoop
_MODULES = []  # type: List[str]
_CONN_MAP = {}  # type: dict


def getDBConfig(app_label: str, modules: List[str]) -> dict:
    """
    DB Config factory, for use in testing.

    :param app_label: Label of the app (must be distinct for multiple apps).
    :param modules: List of modules to look for models in.
    """
    return _generate_config(
        _TORTOISE_TEST_DB,
        app_modules={app_label: modules},
        testing=True,
        connection_label=app_label,
    )


async def _init_db(config: dict) -> None:
    try:
        await Tortoise.init(config)
        await Tortoise._drop_databases()
    except DBConnectionError:  # pragma: nocoverage
        pass

    await Tortoise.init(config, _create_db=True)
    await Tortoise.generate_schemas(safe=False)


def _restore_default() -> None:
    Tortoise.apps = {}
    Tortoise._connections = _CONNECTIONS.copy()
    current_transaction_map.update(_CONN_MAP)
    Tortoise._init_apps(_CONFIG["apps"])
    Tortoise._inited = True


def initializer(
    modules: List[str], db_url: Optional[str] = None, loop: Optional[BaseSelectorEventLoop] = None
) -> None:
    """
    Sets up the DB for testing. Must be called as part of test environment setup.

    :param modules: List of modules to look for models in.
    :param db_url: The db_url, defaults to ``sqlite://:memory``.
    :param loop: Optional event loop.
    """
    # pylint: disable=W0603
    global _CONFIG
    global _CONNECTIONS
    global _SELECTOR
    global _LOOP
    global _TORTOISE_TEST_DB
    global _MODULES
    global _CONN_MAP
    _MODULES = modules
    if db_url is not None:  # pragma: nobranch
        _TORTOISE_TEST_DB = db_url
    _CONFIG = getDBConfig(app_label="models", modules=_MODULES)

    loop = loop or asyncio.get_event_loop()
    _LOOP = loop
    _SELECTOR = loop._selector  # type: ignore
    loop.run_until_complete(_init_db(_CONFIG))
    _CONNECTIONS = Tortoise._connections.copy()
    _CONN_MAP = current_transaction_map.copy()
    Tortoise.apps = {}
    Tortoise._connections = {}
    Tortoise._inited = False


def finalizer() -> None:
    """
    Cleans up the DB after testing. Must be called as part of the test environment teardown.
    """
    _restore_default()
    loop = _LOOP
    loop._selector = _SELECTOR
    loop.run_until_complete(Tortoise._drop_databases())


def env_initializer() -> None:
    """
    Calls ``initializer()`` with parameters mapped from environment variables.

    ``TORTOISE_TEST_MODULES``:
        A comma-separated list of modules to include *(required)*
    ``TORTOISE_TEST_DB``:
        The db_url of the test db. *(optional*)
    """
    modules = str(_os.environ.get("TORTOISE_TEST_MODULES", "tortoise.tests.testmodels")).split(",")
    db_url = _os.environ.get("TORTOISE_TEST_DB", "sqlite://:memory:")
    if not modules:  # pragma: nocoverage
        raise Exception("TORTOISE_TEST_MODULES envvar not defined")
    initializer(modules, db_url=db_url)


class SimpleTestCase(_TestCase):  # type: ignore
    """
    The Tortoise base test class.

    This will ensure that your DB environment has a test double set up for use.

    An asyncio capable test class that provides some helper functions.

    Will run any ``test_*()`` function either as sync or async, depending
    on the signature of the function.
    If you specify ``async test_*()`` then it will run it in an event loop.

    Based on `asynctest <http://asynctest.readthedocs.io/>`_
    """

    use_default_loop = True

    def _init_loop(self) -> None:
        # pylint: disable=W0201
        if self.use_default_loop:
            self.loop = _LOOP
            loop = None
        else:  # pragma: nocoverage
            loop = self.loop = asyncio.new_event_loop()

        policy = _Policy(asyncio.get_event_loop_policy(), loop, self.forbid_get_event_loop)

        asyncio.set_event_loop_policy(policy)

        self.loop = self._patch_loop(self.loop)

    async def _setUpDB(self) -> None:
        pass

    async def _tearDownDB(self) -> None:
        pass

    def _setUp(self) -> None:
        self._init_loop()

        # initialize post-test checks
        test = getattr(self, self._testMethodName)
        checker = getattr(test, _fail_on._FAIL_ON_ATTR, None)
        self._checker = checker or _fail_on._fail_on()  # pylint: disable=W0201
        self._checker.before_test(self)

        self.loop.run_until_complete(self._setUpDB())
        if asyncio.iscoroutinefunction(self.setUp):
            self.loop.run_until_complete(self.setUp())
        else:
            self.setUp()

        # don't take into account if the loop ran during setUp
        self.loop._asynctest_ran = False

    def _tearDown(self) -> None:
        if asyncio.iscoroutinefunction(self.tearDown):
            self.loop.run_until_complete(self.tearDown())
        else:
            self.tearDown()
        self.loop.run_until_complete(self._tearDownDB())
        Tortoise.apps = {}
        Tortoise._connections = {}
        Tortoise._inited = False

        # post-test checks
        self._checker.check_test(self)


class IsolatedTestCase(SimpleTestCase):
    """
    An asyncio capable test class that will ensure that an isolated test db
    is available for each test.

    It will create and destroy a new DB instance for every test.
    This is obviously slow, but guarantees a fresh DB.
    """

    # pylint: disable=C0103,W0201
    async def _setUpDB(self) -> None:
        config = getDBConfig(app_label="models", modules=_MODULES)
        await Tortoise.init(config, _create_db=True)
        await Tortoise.generate_schemas(safe=False)
        self._connections = Tortoise._connections.copy()

    async def _tearDownDB(self) -> None:
        Tortoise._connections = self._connections.copy()
        await Tortoise._drop_databases()


class TestCase(SimpleTestCase):
    """
    An asyncio capable test class that will ensure that each test will be run at
    separate transaction that will rollback on finish.
    """

    async def _setUpDB(self) -> None:
        _restore_default()
        self.transaction = await start_transaction()  # pylint: disable=W0201

    async def _tearDownDB(self) -> None:
        _restore_default()
        await self.transaction.rollback()


def requireCapability(connection_name: str = "models", **conditions: Any):
    """
    Skip a test if the required capabilities are not matched.

    .. note::
        The database must be initialized *before* the decorated test runs.

    Usage:

    .. code-block:: python3

        @requireCapability(dialect='sqlite')
        async def test_run_sqlite_only(self):
            ...

    :param connection_name: name of the connection to retrieve capabilities from.
    :param conditions: capability tests which must all pass for the test to run.
    """

    def decorator(test_item):
        @wraps(test_item)
        def skip_wrapper(*args, **kwargs):
            db = Tortoise.get_connection(connection_name)
            for key, val in conditions.items():
                if getattr(db.capabilities, key) != val:
                    raise SkipTest("Capability {key} != {val}".format(key=key, val=val))
            return test_item(*args, **kwargs)

        return skip_wrapper

    return decorator
