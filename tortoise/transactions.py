from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING, TypeVar, cast

from tortoise import connections
from tortoise.exceptions import ParamsError

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.backends.base.client import BaseDBAsyncClient, TransactionContext

T = TypeVar("T")
FuncType = Callable[..., T]
F = TypeVar("F", bound=FuncType)


def _get_connection(connection_name: str | None) -> BaseDBAsyncClient:
    if connection_name:
        connection = connections.get(connection_name)
    elif len(connections.db_config) == 1:
        connection_name = next(iter(connections.db_config.keys()))
        connection = connections.get(connection_name)
    else:
        raise ParamsError(
            "You are running with multiple databases, so you should specify"
            f" connection_name: {list(connections.db_config)}"
        )
    return connection


def in_transaction(connection_name: str | None = None) -> TransactionContext:
    """
    Transaction context manager.

    You can run your code inside ``async with in_transaction():`` statement to run it
    into one transaction. If error occurs transaction will rollback.

    :param connection_name: name of connection to run with, optional if you have only
                            one db connection
    """
    connection = _get_connection(connection_name)
    return connection._in_transaction()


def atomic(connection_name: str | None = None) -> Callable[[F], F]:
    """
    Transaction decorator.

    You can wrap your function with this decorator to run it into one transaction.
    If error occurs transaction will rollback.

    :param connection_name: name of connection to run with, optional if you have only
                            one db connection
    """

    def wrapper(func: F) -> F:
        @wraps(func)
        async def wrapped(*args, **kwargs) -> T:
            async with in_transaction(connection_name):
                return await func(*args, **kwargs)

        return cast(F, wrapped)

    return wrapper
