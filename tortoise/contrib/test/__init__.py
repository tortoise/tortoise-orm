import asyncio
import os as _os
import unittest
from asyncio.events import AbstractEventLoop
from functools import wraps
from types import ModuleType
from typing import Any, Callable, Iterable, List, Optional, Union
from unittest import SkipTest, expectedFailure, skip, skipIf, skipUnless
from unittest.result import TestResult

from asynctest import TestCase as _TestCase
from asynctest import _fail_on
from asynctest.case import _Policy

from tortoise import Model, Tortoise
from tortoise.backends.base.config_generator import generate_config as _generate_config
from tortoise.exceptions import DBConnectionError
from tortoise.transactions import current_transaction_map

__all__ = (
    "SimpleTestCase",
    "TestCase",
    "TruncationTestCase",
    "IsolatedTestCase",
    "getDBConfig",
    "requireCapability",
    "env_initializer",
    "initializer",
    "finalizer",
    "SkipTest",
    "expectedFailure",
    "skip",
    "skipIf",
    "skipUnless",
)
_TORTOISE_TEST_DB = "sqlite://:memory:"
# pylint: disable=W0201

expectedFailure.__doc__ = """
Mark test as expecting failiure.

On success it will be marked as unexpected success.
"""

_CONFIG: dict = {}
_CONNECTIONS: dict = {}
_SELECTOR = None
_LOOP: AbstractEventLoop = None  # type: ignore
_MODULES: Iterable[Union[str, ModuleType]] = []
_CONN_MAP: dict = {}


def getDBConfig(app_label: str, modules: Iterable[Union[str, ModuleType]]) -> dict:
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
    modules: Iterable[Union[str, ModuleType]],
    db_url: Optional[str] = None,
    app_label: str = "models",
    loop: Optional[AbstractEventLoop] = None,
) -> None:
    """
    Sets up the DB for testing. Must be called as part of test environment setup.

    :param modules: List of modules to look for models in.
    :param db_url: The db_url, defaults to ``sqlite://:memory``.
    :param app_label: The name of the APP to initialise the modules in, defaults to "models"
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
    _CONFIG = getDBConfig(app_label=app_label, modules=_MODULES)

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
    loop._selector = _SELECTOR  # type: ignore
    loop.run_until_complete(Tortoise._drop_databases())


def env_initializer() -> None:  # pragma: nocoverage
    """
    Calls ``initializer()`` with parameters mapped from environment variables.

    ``TORTOISE_TEST_MODULES``:
        A comma-separated list of modules to include *(required)*
    ``TORTOISE_TEST_APP``:
        The name of the APP to initialise the modules in *(optional)*

        If not provided, it will default to "models".
    ``TORTOISE_TEST_DB``:
        The db_url of the test db. *(optional*)

        If not provided, it will default to an in-memory SQLite DB.
    """
    modules = str(_os.environ.get("TORTOISE_TEST_MODULES", "tests.testmodels")).split(",")
    db_url = _os.environ.get("TORTOISE_TEST_DB", "sqlite://:memory:")
    app_label = _os.environ.get("TORTOISE_TEST_APP", "models")
    if not modules:  # pragma: nocoverage
        raise Exception("TORTOISE_TEST_MODULES envvar not defined")
    initializer(modules, db_url=db_url, app_label=app_label)


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

    async def _setUp(self) -> None:

        # initialize post-test checks
        test = getattr(self, self._testMethodName)
        checker = getattr(test, _fail_on._FAIL_ON_ATTR, None)
        self._checker = checker or _fail_on._fail_on()
        self._checker.before_test(self)

        await self._setUpDB()
        if asyncio.iscoroutinefunction(self.setUp):
            await self.setUp()
        else:
            self.setUp()

        # don't take into account if the loop ran during setUp
        self.loop._asynctest_ran = False  # type: ignore

    async def _tearDown(self) -> None:
        if asyncio.iscoroutinefunction(self.tearDown):
            await self.tearDown()
        else:
            self.tearDown()
        await self._tearDownDB()
        Tortoise.apps = {}
        Tortoise._connections = {}
        Tortoise._inited = False

        # post-test checks
        self._checker.check_test(self)

    # Override unittest.TestCase methods which call setUp() and tearDown()
    def run(self, result: Optional[TestResult] = None) -> Optional[TestResult]:
        orig_result = result
        if result is None:  # pragma: nocoverage
            result = self.defaultTestResult()
            startTestRun = getattr(result, "startTestRun", None)
            if startTestRun is not None:
                startTestRun()

        result.startTest(self)

        testMethod = getattr(self, self._testMethodName)
        if getattr(self.__class__, "__unittest_skip__", False) or getattr(
            testMethod, "__unittest_skip__", False
        ):
            # If the class or method was skipped.
            try:
                skip_why = getattr(self.__class__, "__unittest_skip_why__", "") or getattr(
                    testMethod, "__unittest_skip_why__", ""
                )
                self._addSkip(result, self, skip_why)
            finally:
                result.stopTest(self)
            return None
        expecting_failure = getattr(testMethod, "__unittest_expecting_failure__", False)
        outcome = unittest.case._Outcome(result)  # type: ignore
        try:
            self._outcome = outcome

            self._init_loop()

            self.loop.run_until_complete(self._run_outcome(outcome, expecting_failure, testMethod))

            self.loop.run_until_complete(self.doCleanups())
            self._unset_loop()
            for test, reason in outcome.skipped:
                self._addSkip(result, test, reason)
            self._feedErrorsToResult(result, outcome.errors)
            if outcome.success:
                if expecting_failure:
                    if outcome.expectedFailure:
                        self._addExpectedFailure(result, outcome.expectedFailure)
                    else:  # pragma: nocoverage
                        self._addUnexpectedSuccess(result)
                else:
                    result.addSuccess(self)
            return result
        finally:
            result.stopTest(self)
            if orig_result is None:  # pragma: nocoverage
                stopTestRun = getattr(result, "stopTestRun", None)
                if stopTestRun is not None:
                    stopTestRun()  # pylint: disable=E1102

            # explicitly break reference cycles:
            # outcome.errors -> frame -> outcome -> outcome.errors
            # outcome.expectedFailure -> frame -> outcome -> outcome.expectedFailure
            outcome.errors.clear()
            outcome.expectedFailure = None

            # clear the outcome, no more needed
            self._outcome = None

    def assertListSortEqual(self, list1: List[Any], list2: List[Any], msg: Any = ...) -> None:
        if isinstance(list1[0], Model):
            super().assertListEqual(
                sorted(list1, key=lambda x: x.pk), sorted(list2, key=lambda x: x.pk)
            )
        elif isinstance(list1[0], tuple):
            super().assertListEqual(sorted(list1), sorted(list2))

    async def _run_outcome(self, outcome, expecting_failure: bool, testMethod: Callable) -> None:
        with outcome.testPartExecutor(self):
            await self._setUp()
        if outcome.success:
            outcome.expecting_failure = expecting_failure
            with outcome.testPartExecutor(self, isTest=True):
                await self._run_test_method(testMethod)
            outcome.expecting_failure = False
            with outcome.testPartExecutor(self):
                await self._tearDown()

    async def _run_test_method(self, method: Callable) -> None:
        # If the method is a coroutine or returns a coroutine, run it on the
        # loop
        result = method()
        if asyncio.iscoroutine(result):
            await result


class IsolatedTestCase(SimpleTestCase):
    """
    An asyncio capable test class that will ensure that an isolated test db
    is available for each test.

    Use this if your test needs perfect isolation.

    Note to use ``{}`` as a string-replacement parameter, for your DB_URL.
    That will create a randomised database name.

    It will create and destroy a new DB instance for every test.
    This is obviously slow, but guarantees a fresh DB.

    If you define a ``tortoise_test_modules`` list, it overrides the DB setup module for the tests.
    """

    tortoise_test_modules: Iterable[Union[str, ModuleType]] = []

    async def _setUpDB(self) -> None:
        config = getDBConfig(app_label="models", modules=self.tortoise_test_modules or _MODULES)
        await Tortoise.init(config, _create_db=True)
        await Tortoise.generate_schemas(safe=False)
        self._connections = Tortoise._connections.copy()

    async def _tearDownDB(self) -> None:
        Tortoise._connections = self._connections.copy()
        await Tortoise._drop_databases()


class TruncationTestCase(SimpleTestCase):
    """
    An asyncio capable test class that will truncate the tables after a test.

    Use this when your tests contain transactions.

    This is slower than ``TestCase`` but faster than ``IsolatedTestCase``.
    Note that usage of this does not guarantee that auto-number-pks will be reset to 1.
    """

    async def _setUpDB(self) -> None:
        _restore_default()

    async def _tearDownDB(self) -> None:
        _restore_default()
        # TODO: This is a naive implementation: Will fail to clear M2M and non-cascade foreign keys
        for app in Tortoise.apps.values():
            for model in app.values():
                quote_char = model._meta.db.query_class._builder().QUOTE_CHAR
                await model._meta.db.execute_script(  # nosec
                    f"DELETE FROM {quote_char}{model._meta.db_table}{quote_char}"
                )


class TransactionTestContext:
    __slots__ = ("connection", "connection_name", "token")

    def __init__(self, connection) -> None:
        self.connection = connection
        self.connection_name = connection.connection_name

    async def __aenter__(self):
        current_transaction = current_transaction_map[self.connection_name]
        self.token = current_transaction.set(self.connection)
        if hasattr(self.connection, "_parent"):
            self.connection._connection = await self.connection._parent._pool.acquire()
        await self.connection.start()
        return self.connection

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.connection.rollback()
        if hasattr(self.connection, "_parent"):
            await self.connection._parent._pool.release(self.connection._connection)
        current_transaction_map[self.connection_name].reset(self.token)


class TestCase(TruncationTestCase):
    """
    An asyncio capable test class that will ensure that each test will be run at
    separate transaction that will rollback on finish.

    This is a fast test runner. Don't use it if your test uses transactions.
    """

    async def _run_outcome(self, outcome, expecting_failure, testMethod) -> None:
        _restore_default()
        self.__db__ = Tortoise.get_connection("models")
        if self.__db__.capabilities.supports_transactions:
            connection = self.__db__._in_transaction().connection
            async with TransactionTestContext(connection):
                await super()._run_outcome(outcome, expecting_failure, testMethod)
        else:
            await super()._run_outcome(outcome, expecting_failure, testMethod)

    async def _setUpDB(self) -> None:
        pass

    async def _tearDownDB(self) -> None:
        if self.__db__.capabilities.supports_transactions:
            _restore_default()
        else:
            await super()._tearDownDB()


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

    Or to conditionally skip a class:

    .. code-block:: python3

        @requireCapability(dialect='sqlite')
        class TestSqlite(test.TestCase):
            ...

    :param connection_name: name of the connection to retrieve capabilities from.
    :param conditions: capability tests which must all pass for the test to run.
    """

    def decorator(test_item):
        if not isinstance(test_item, type):

            @wraps(test_item)
            def skip_wrapper(*args, **kwargs):
                db = Tortoise.get_connection(connection_name)
                for key, val in conditions.items():
                    if getattr(db.capabilities, key) != val:
                        raise SkipTest(f"Capability {key} != {val}")
                return test_item(*args, **kwargs)

            return skip_wrapper

        # Assume a class is decorated
        funcs = {
            var: getattr(test_item, var)
            for var in dir(test_item)
            if var.startswith("test_") and callable(getattr(test_item, var))
        }
        for name, func in funcs.items():
            setattr(
                test_item,
                name,
                requireCapability(connection_name=connection_name, **conditions)(func),
            )

        return test_item

    return decorator
