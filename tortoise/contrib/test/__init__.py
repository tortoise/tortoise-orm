import asyncio
import inspect
import os as _os
import sys
import typing
import unittest
from asyncio.events import AbstractEventLoop
from functools import partial, wraps
from types import ModuleType
from typing import Any, Callable, Coroutine, Iterable, List, Optional, TypeVar, Union
from unittest import SkipTest, expectedFailure, skip, skipIf, skipUnless

from tortoise import Model, Tortoise, connections
from tortoise.backends.base.config_generator import generate_config as _generate_config
from tortoise.exceptions import DBConnectionError, OperationalError

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec


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
    "init_memory_sqlite",
)
_TORTOISE_TEST_DB = "sqlite://:memory:"
# pylint: disable=W0201

expectedFailure.__doc__ = """
Mark test as expecting failure.

On success it will be marked as unexpected success.
"""

_CONFIG: dict = {}
_CONNECTIONS: dict = {}
_LOOP: AbstractEventLoop = None  # type: ignore
_MODULES: Iterable[Union[str, ModuleType]] = []
_CONN_CONFIG: dict = {}


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
    # Placing init outside the try block since it doesn't
    # establish connections to the DB eagerly.
    await Tortoise.init(config)
    try:
        await Tortoise._drop_databases()
    except (DBConnectionError, OperationalError):  # pragma: nocoverage
        pass

    await Tortoise.init(config, _create_db=True)
    await Tortoise.generate_schemas(safe=False)


def _restore_default() -> None:
    Tortoise.apps = {}
    connections._get_storage().update(_CONNECTIONS.copy())
    connections._db_config = _CONN_CONFIG.copy()
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
    global _LOOP
    global _TORTOISE_TEST_DB
    global _MODULES
    global _CONN_CONFIG
    _MODULES = modules
    if db_url is not None:  # pragma: nobranch
        _TORTOISE_TEST_DB = db_url
    _CONFIG = getDBConfig(app_label=app_label, modules=_MODULES)
    loop = loop or asyncio.get_event_loop()
    _LOOP = loop
    loop.run_until_complete(_init_db(_CONFIG))
    _CONNECTIONS = connections._copy_storage()
    _CONN_CONFIG = connections.db_config.copy()
    connections._clear_storage()
    connections.db_config.clear()
    Tortoise.apps = {}
    Tortoise._inited = False


def finalizer() -> None:
    """
    Cleans up the DB after testing. Must be called as part of the test environment teardown.
    """
    _restore_default()
    loop = _LOOP
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


class SimpleTestCase(unittest.IsolatedAsyncioTestCase):
    """
    The Tortoise base test class.

    This will ensure that your DB environment has a test double set up for use.

    An asyncio capable test class that provides some helper functions.

    Will run any ``test_*()`` function either as sync or async, depending
    on the signature of the function.
    If you specify ``async test_*()`` then it will run it in an event loop.

    Based on `asynctest <http://asynctest.readthedocs.io/>`_
    """

    def _setupAsyncioRunner(self) -> None:
        if hasattr(asyncio, "Runner"):  # For python3.11+
            runner = asyncio.Runner(debug=True, loop_factory=asyncio.get_event_loop)
            self._asyncioRunner = runner

    def _tearDownAsyncioRunner(self) -> None:
        # Override runner tear down to avoid eventloop closing before testing completed.
        pass

    async def _setUpDB(self) -> None:
        pass

    async def _tearDownDB(self) -> None:
        pass

    def _setupAsyncioLoop(self):
        loop = asyncio.get_event_loop()
        loop.set_debug(True)
        self._asyncioTestLoop = loop
        fut = loop.create_future()
        self._asyncioCallsTask = loop.create_task(self._asyncioLoopRunner(fut))  # type: ignore
        loop.run_until_complete(fut)

    def _tearDownAsyncioLoop(self):
        loop = self._asyncioTestLoop
        self._asyncioTestLoop = None  # type: ignore
        self._asyncioCallsQueue.put_nowait(None)  # type: ignore
        loop.run_until_complete(self._asyncioCallsQueue.join())  # type: ignore

    async def asyncSetUp(self) -> None:
        await self._setUpDB()

    def _reset_conn_state(self) -> None:
        # clearing the storage and db config
        connections._clear_storage()
        connections.db_config.clear()

    async def asyncTearDown(self) -> None:
        await self._tearDownDB()
        self._reset_conn_state()
        Tortoise.apps = {}
        Tortoise._inited = False

    def assertListSortEqual(
        self, list1: List[Any], list2: List[Any], msg: Any = ..., sorted_key: Optional[str] = None
    ) -> None:
        if isinstance(list1[0], Model):
            super().assertListEqual(
                sorted(list1, key=lambda x: x.pk), sorted(list2, key=lambda x: x.pk), msg=msg
            )
        elif isinstance(list1[0], dict) and sorted_key:
            super().assertListEqual(
                sorted(list1, key=lambda x: x[sorted_key]),
                sorted(list2, key=lambda x: x[sorted_key]),
                msg=msg,
            )
        else:
            super().assertListEqual(sorted(list1), sorted(list2), msg=msg)


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
        await super()._setUpDB()
        config = getDBConfig(app_label="models", modules=self.tortoise_test_modules or _MODULES)
        await Tortoise.init(config, _create_db=True)
        await Tortoise.generate_schemas(safe=False)

    async def _tearDownDB(self) -> None:
        await Tortoise._drop_databases()


class TruncationTestCase(SimpleTestCase):
    """
    An asyncio capable test class that will truncate the tables after a test.

    Use this when your tests contain transactions.

    This is slower than ``TestCase`` but faster than ``IsolatedTestCase``.
    Note that usage of this does not guarantee that auto-number-pks will be reset to 1.
    """

    async def _setUpDB(self) -> None:
        await super()._setUpDB()
        _restore_default()

    async def _tearDownDB(self) -> None:
        _restore_default()
        # TODO: This is a naive implementation: Will fail to clear M2M and non-cascade foreign keys
        for app in Tortoise.apps.values():
            for model in app.values():
                quote_char = model._meta.db.query_class._builder().QUOTE_CHAR
                await model._meta.db.execute_script(
                    f"DELETE FROM {quote_char}{model._meta.db_table}{quote_char}"  # nosec
                )
        await super()._tearDownDB()


class TransactionTestContext:
    __slots__ = ("connection", "connection_name", "token", "uses_pool")

    def __init__(self, connection) -> None:
        self.connection = connection
        self.connection_name = connection.connection_name
        self.uses_pool = hasattr(self.connection._parent, "_pool")

    async def ensure_connection(self) -> None:
        is_conn_established = self.connection._connection is not None
        if self.uses_pool:
            is_conn_established = self.connection._parent._pool is not None

        # If the underlying pool/connection hasn't been established then
        # first create the pool/connection
        if not is_conn_established:
            await self.connection._parent.create_connection(with_db=True)

        if self.uses_pool:
            self.connection._connection = await self.connection._parent._pool.acquire()
        else:
            self.connection._connection = self.connection._parent._connection

    async def __aenter__(self):
        await self.ensure_connection()
        self.token = connections.set(self.connection_name, self.connection)
        await self.connection.start()
        return self.connection

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.connection.rollback()
        if self.uses_pool:
            await self.connection._parent._pool.release(self.connection._connection)
        connections.reset(self.token)


class TestCase(TruncationTestCase):
    """
    An asyncio capable test class that will ensure that each test will be run at
    separate transaction that will rollback on finish.

    This is a fast test runner. Don't use it if your test uses transactions.
    """

    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        self._db = connections.get("models")
        self._transaction = TransactionTestContext(self._db._in_transaction().connection)
        await self._transaction.__aenter__()  # type: ignore

    async def asyncTearDown(self) -> None:
        await self._transaction.__aexit__(None, None, None)
        await super().asyncTearDown()

    async def _tearDownDB(self) -> None:
        if self._db.capabilities.supports_transactions:
            _restore_default()
        else:
            await super()._tearDownDB()


def requireCapability(connection_name: str = "models", **conditions: Any) -> Callable:
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

            def check_capabilities() -> None:
                db = connections.get(connection_name)
                for key, val in conditions.items():
                    if getattr(db.capabilities, key) != val:
                        raise SkipTest(f"Capability {key} != {val}")

            if hasattr(asyncio, "Runner") and inspect.iscoroutinefunction(test_item):
                # For python3.11+

                @wraps(test_item)
                async def skip_wrapper(*args, **kwargs):
                    check_capabilities()
                    return await test_item(*args, **kwargs)

            else:

                @wraps(test_item)
                def skip_wrapper(*args, **kwargs):
                    check_capabilities()
                    return test_item(*args, **kwargs)

            return skip_wrapper

        # Assume a class is decorated
        funcs = {
            var: f
            for var in dir(test_item)
            if var.startswith("test_") and callable(f := getattr(test_item, var))
        }
        for name, func in funcs.items():
            setattr(
                test_item,
                name,
                requireCapability(connection_name=connection_name, **conditions)(func),
            )

        return test_item

    return decorator


T = TypeVar("T")
P = ParamSpec("P")
AsyncFunc = Callable[P, Coroutine[None, None, T]]
AsyncFuncDeco = Callable[..., AsyncFunc]
ModulesConfigType = Union[str, List[str]]


@typing.overload
def init_memory_sqlite(models: Union[ModulesConfigType, None] = None) -> AsyncFuncDeco: ...


@typing.overload
def init_memory_sqlite(models: AsyncFunc) -> AsyncFunc: ...


def init_memory_sqlite(
    models: Union[ModulesConfigType, AsyncFunc, None] = None
) -> Union[AsyncFunc, AsyncFuncDeco]:
    """
    For single file style to run code with memory sqlite

    :param models: list_of_modules that should be discovered for models, default to ['__main__'].

    Usage:

    .. code-block:: python3

        from tortoise import fields, models, run_async
        from tortoise.contrib.test import init_memory_sqlite

        class MyModel(models.Model):
            id = fields.IntField(primary_key=True)
            name = fields.TextField()

        @init_memory_sqlite
        async def run():
            obj = await MyModel.create(name='')
            assert obj.id == 1

        if __name__ == '__main__'
            run_async(run)


    Custom models example:

    .. code-block:: python3

        @init_memory_sqlite(models=['app.models', 'aerich.models'])
        async def run():
            ...
    """

    def wrapper(func: AsyncFunc, ms: List[str]):
        @wraps(func)
        async def runner(*args, **kwargs) -> T:
            await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ms})
            await Tortoise.generate_schemas()
            return await func(*args, **kwargs)

        return runner

    default_models = ["__main__"]
    if inspect.iscoroutinefunction(models):
        return wrapper(models, default_models)
    if models is None:
        models = default_models
    elif isinstance(models, str):
        models = [models]
    return partial(wrapper, ms=models)
