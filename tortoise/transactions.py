from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Optional, TypeVar, cast

from tortoise.exceptions import ParamsError

current_transaction_map: dict = {}

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.backends.base.client import BaseDBAsyncClient, TransactionContext

FuncType = Callable[..., Any]
F = TypeVar("F", bound=FuncType)


def get_connection(connection_name: Optional[str]) -> "BaseDBAsyncClient":
    from tortoise import Tortoise

    if connection_name:
        connection = current_transaction_map[connection_name].get()
    elif len(Tortoise._connections) == 1:
        connection_name = list(Tortoise._connections.keys())[0]
        connection = current_transaction_map[connection_name].get()
    else:
        raise ParamsError(
            "You are running with multiple databases, so you should specify"
            f" connection_name: {list(Tortoise._connections.keys())}"
        )
    return connection


def in_transaction(connection_name: Optional[str] = None) -> "TransactionContext":
    """
    Transaction context manager.

    You can run your code inside ``async with in_transaction():`` statement to run it
    into one transaction. If error occurs transaction will rollback.

    :param connection_name: name of connection to run with, optional if you have only
                            one db connection
    """
    connection = get_connection(connection_name)
    return connection._in_transaction()


def atomic(connection_name: Optional[str] = None) -> Callable[[F], F]:
    """
    Transaction decorator.

    You can wrap your function with this decorator to run it into one transaction.
    If error occurs transaction will rollback.

    :param connection_name: name of connection to run with, optional if you have only
                            one db connection
    """

    def wrapper(func: F) -> F:
        @wraps(func)
        async def wrapped(*args, **kwargs):
            async with in_transaction(connection_name):
                return await func(*args, **kwargs)

        return cast(F, wrapped)

    return wrapper
