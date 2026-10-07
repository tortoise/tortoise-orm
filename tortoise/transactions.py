from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING, TypeVar, cast

from tortoise.backends.base.client import TransactionalDBClient, run_on_commit_callbacks
from tortoise.connection import get_connections
from tortoise.exceptions import ParamsError

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.backends.base.client import (
        BaseDBAsyncClient,
        OnCommitCallback,
        TransactionContext,
    )

T = TypeVar("T")
FuncType = Callable[..., T]
F = TypeVar("F", bound=FuncType)


def _get_connection(connection_name: str | None) -> BaseDBAsyncClient:
    conn_handler = get_connections()
    if connection_name:
        connection = conn_handler.get(connection_name)
    elif len(conn_handler.db_config) == 1:
        connection_name = next(iter(conn_handler.db_config.keys()))
        connection = conn_handler.get(connection_name)
    else:
        raise ParamsError(
            "You are running with multiple databases, so you should specify"
            f" connection_name: {list(conn_handler.db_config)}"
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


async def on_commit(callback: OnCommitCallback, connection_name: str | None = None) -> None:
    """
    Run a callback once the current transaction commits.

    The callback is dropped on rollback, including a savepoint rollback of the block that
    registered it, and runs immediately outside a transaction.

    :param callback: Callable taking no arguments, sync or async.
    :param connection_name: name of connection to run with, optional if you have only
                            one db connection
    :raises ExceptionGroup: If callbacks raise, once all of them have run.
    """
    connection = _get_connection(connection_name)
    if isinstance(connection, TransactionalDBClient) and connection._on_commit_frames:
        connection._on_commit_frames[-1].append(callback)
    else:
        await run_on_commit_callbacks([callback])


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
