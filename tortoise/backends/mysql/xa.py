# -*- coding: utf-8 -*-
# @Time    : 2023/2/13 17:53
# @Author  : Tuffy
# @Description : 

# -*- coding: utf-8 -*-
# @Time    : 2022/7/26 16:07
# @Author  : Tuffy
# @Description :
from typing import Optional

from pymysql.constants import COMMAND
from tortoise import connections
from tortoise.backends.base.client import TransactionContextPooled
from tortoise.backends.mysql.client import MySQLClient, TransactionWrapper, translate_exceptions
from tortoise.exceptions import ParamsError, TransactionManagementError


class XATransactionWrapper(TransactionWrapper):
    def __init__(self, connection: MySQLClient, transaction_id: str) -> None:
        super().__init__(connection)
        self.transaction_id = transaction_id

    @translate_exceptions
    async def start(self) -> None:
        await self._connection._execute_command(COMMAND.COM_QUERY, f"XA START '{self.transaction_id}'")
        await self._connection._read_ok_packet()
        self._finalized = False

    async def commit(self) -> None:
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        await self._connection._execute_command(COMMAND.COM_QUERY, f"XA END '{self.transaction_id}'")
        await self._connection._read_ok_packet()
        await self._connection._execute_command(COMMAND.COM_QUERY, f"XA COMMIT '{self.transaction_id}'")
        await self._connection._read_ok_packet()
        self._finalized = True

    async def rollback(self) -> None:
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        await self._connection._execute_command(COMMAND.COM_QUERY, f"XA END '{self.transaction_id}'")
        await self._connection._read_ok_packet()
        await self._connection._execute_command(COMMAND.COM_QUERY, f"XA ROLLBACK '{self.transaction_id}'")
        await self._connection._read_ok_packet()
        self._finalized = True


class XAMySQLClient(MySQLClient):
    def xa_in_transaction(self, transaction_id: str) -> "TransactionContext":
        return TransactionContextPooled(XATransactionWrapper(self, transaction_id))


def _get_connection(connection_name: Optional[str]) -> "BaseDBAsyncClient":
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


def xa_in_transaction(transaction_id: str, connection_name: Optional[str] = None) -> "TransactionContext":
    connection = _get_connection(connection_name)
    return XAMySQLClient.xa_in_transaction(connection, transaction_id)
