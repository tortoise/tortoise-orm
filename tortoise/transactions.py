from functools import wraps
from typing import Callable, Optional, Dict  # noqa

from tortoise.backends.base.client import BaseDBAsyncClient, BaseTransactionWrapper
from tortoise.exceptions import ParamsError

current_transaction_map = {}  # type: Dict


def _get_connection(connection_name: Optional[str]) -> BaseDBAsyncClient:
    from tortoise import Tortoise
    if connection_name:
        connection = Tortoise.get_connection(connection_name)
    elif len(Tortoise._connections) == 1:
        connection = list(Tortoise._connections.values())[0]
    else:
        raise ParamsError(
            'You are running with multiple databases, so you should specify connection_name'
        )
    return connection


def in_transaction(connection_name: Optional[str] = None) -> BaseTransactionWrapper:
    """
    Transaction context manager.

    You can run your code inside ``async with in_transaction():`` statement to run it
    into one transaction. If error occurs transaction will rollback.

    :param connection_name: name of connection to run with, optional if you have only
                            one db connection
    """
    connection = _get_connection(connection_name)
    single_connection = connection._in_transaction()
    return single_connection


def atomic(connection_name: Optional[str] = None) -> Callable:
    """
    Transaction decorator.

    You can wrap your function with this decorator to run it into one transaction.
    If error occurs transaction will rollback.

    :param connection_name: name of connection to run with, optional if you have only
                            one db connection
    """

    def wrapper(func):
        @wraps(func)
        async def wrapped(*args, **kwargs):
            connection = _get_connection(connection_name)
            async with connection._in_transaction():
                return await func(*args, **kwargs)

        return wrapped

    return wrapper


async def start_transaction(connection_name: Optional[str] = None) -> BaseTransactionWrapper:
    """
    Function to manually control your transaction.

    Returns transaction object with ``.rollback()`` and ``.commit()`` methods.
    All db calls in same coroutine context will run into transaction
    before ending transaction with above methods.

    :param connection_name: name of connection to run with, optional if you have only
                            one db connection
    """
    connection = _get_connection(connection_name)
    transaction = connection._in_transaction()
    await transaction.start()
    return transaction
