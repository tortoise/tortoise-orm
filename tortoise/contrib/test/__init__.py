"""
Modern testing utilities for Tortoise ORM.

Use tortoise_test_context() with pytest fixtures:

    @pytest_asyncio.fixture
    async def db():
        async with tortoise_test_context(["myapp.models"]) as ctx:
            yield ctx

    @pytest.mark.asyncio
    async def test_example(db):
        user = await User.create(name="Test")
        assert user.id is not None

For capability-based test skipping:

    @requireCapability(dialect="sqlite")
    @pytest.mark.asyncio
    async def test_sqlite_only(db):
        # This test only runs on SQLite
        ...
"""

from __future__ import annotations

import inspect
import typing
from collections.abc import Callable, Coroutine
from functools import partial, wraps
from typing import ParamSpec, TypeVar, cast
from unittest import SkipTest, expectedFailure, skip, skipIf, skipUnless

from tortoise import Tortoise
from tortoise.connection import get_connection
from tortoise.context import TortoiseContext, tortoise_test_context

T = TypeVar("T")
P = ParamSpec("P")
AsyncFunc = Callable[P, Coroutine[None, None, T]]
AsyncFuncDeco = Callable[..., AsyncFunc]
ModulesConfigType = str | list[str]
MEMORY_SQLITE = "sqlite://:memory:"

__all__ = (
    "MEMORY_SQLITE",
    "TortoiseContext",
    "tortoise_test_context",
    "requireCapability",
    "truncate_all_models",
    "init_memory_sqlite",
    "SkipTest",
    "expectedFailure",
    "skip",
    "skipIf",
    "skipUnless",
)

expectedFailure.__doc__ = """
Mark test as expecting failure.

On success it will be marked as unexpected success.
"""


async def truncate_all_models() -> None:
    """
    Truncate all models in the current context.

    This is a utility function for test cleanup that deletes all rows from
    all registered model tables.

    Note: This is a naive implementation that may fail with M2M relations
    and non-cascade foreign keys.

    Raises:
        ValueError: If Tortoise.apps is not loaded.
    """
    if not Tortoise.apps:
        raise ValueError("apps are not loaded")
    for model in Tortoise.apps.get_models_iterable():
        quote_char = model._meta.db.query_class.SQL_CONTEXT.quote_char
        await model._meta.db.execute_script(
            f"DELETE FROM {quote_char}{model._meta.db_table}{quote_char}"  # nosec
        )


_FT = TypeVar("_FT", bound=Callable[..., typing.Any])


def requireCapability(
    connection_name: str = "models", **conditions: typing.Any
) -> Callable[[_FT], _FT]:
    """
    Skip a test if the required capabilities are not matched.

    .. note::
        The database must be initialized *before* the decorated test runs.

    Usage:

    .. code-block:: python3

        @requireCapability(dialect='sqlite')
        @pytest.mark.asyncio
        async def test_run_sqlite_only(db):
            ...

    Or to conditionally skip a class:

    .. code-block:: python3

        @requireCapability(dialect='sqlite')
        class TestSqlite:
            @pytest.mark.asyncio
            async def test_something(self, db):
                ...

    :param connection_name: name of the connection to retrieve capabilities from.
    :param conditions: capability tests which must all pass for the test to run.
    """

    def decorator(test_item: _FT) -> _FT:
        if not isinstance(test_item, type):

            def check_capabilities() -> None:
                db = get_connection(connection_name)
                for key, val in conditions.items():
                    if getattr(db.capabilities, key) != val:
                        raise SkipTest(f"Capability {key} != {val}")

            if inspect.iscoroutinefunction(test_item):

                @wraps(test_item)
                async def skip_wrapper(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
                    check_capabilities()
                    return await test_item(*args, **kwargs)

            else:

                @wraps(test_item)
                def skip_wrapper(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
                    check_capabilities()
                    return test_item(*args, **kwargs)

            return cast(_FT, skip_wrapper)

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


@typing.overload
def init_memory_sqlite(models: ModulesConfigType | None = None) -> AsyncFuncDeco: ...


@typing.overload
def init_memory_sqlite(models: AsyncFunc) -> AsyncFunc: ...


def init_memory_sqlite(
    models: ModulesConfigType | AsyncFunc | None = None,
) -> AsyncFunc | AsyncFuncDeco:
    """
    Decorator for initializing Tortoise with an in-memory SQLite database.

    This is useful for simple scripts and examples that need a quick database setup.

    :param models: List of modules to load models from. Defaults to ["__main__"].

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

        if __name__ == '__main__':
            run_async(run())

    Custom models example:

    .. code-block:: python3

        @init_memory_sqlite(models=['app.models', 'aerich.models'])
        async def run():
            ...
    """

    def wrapper(func: AsyncFunc, ms: list[str]):
        @wraps(func)
        async def runner(*args, **kwargs) -> T:
            await Tortoise.init(db_url=MEMORY_SQLITE, modules={"models": ms})
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
    else:
        models = cast(list, models)
    return partial(wrapper, ms=models)
