from functools import wraps
from typing import Any, Callable, List, Optional, Tuple, TypeVar

import pyodbc
from aioodbc.cursor import Cursor
from pypika.dialects import MSSQLQuery

from tortoise.backends.mssql.schema_generator import MSSQLSchemaGenerator
from tortoise.backends.odbc.client import ODBCClient
from tortoise.exceptions import IntegrityError, OperationalError

FuncType = Callable[..., Any]
F = TypeVar("F", bound=FuncType)


def translate_exceptions(func: F) -> F:
    @wraps(func)
    async def translate_exceptions_(self, *args):
        try:
            return await func(self, *args)
        except (
            pyodbc.OperationalError,
            pyodbc.ProgrammingError,
            pyodbc.DataError,
            pyodbc.InternalError,
            pyodbc.NotSupportedError,
        ) as exc:
            raise OperationalError(exc)
        except pyodbc.IntegrityError as exc:
            raise IntegrityError(exc)

    return translate_exceptions_  # type: ignore


class MSSQLClient(ODBCClient):
    query_class = MSSQLQuery
    schema_generator = MSSQLSchemaGenerator

    @translate_exceptions
    async def execute_query(
        self, query: str, values: Optional[list] = None
    ) -> Tuple[int, List[dict]]:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            async with connection.cursor() as cursor:  # type:Cursor
                if values:
                    await cursor.execute(query, values)
                else:
                    await cursor.execute(query)
                try:
                    rows = await cursor.fetchall()
                    if rows:
                        fields = [c[0] for c in cursor.description]
                        return cursor.rowcount, [dict(zip(fields, row)) for row in rows]
                except pyodbc.ProgrammingError:
                    pass
                return cursor.rowcount, []

    @translate_exceptions
    async def execute_script(self, query: str) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug(query)
            async with connection.cursor() as cursor:
                await cursor.execute(query)

    @translate_exceptions
    async def execute_insert(self, query: str, values: list) -> int:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            async with connection.cursor() as cursor:
                await cursor.execute(query, values)
                await cursor.execute("SELECT @@IDENTITY")
                return (await cursor.fetchone())[0]

    @translate_exceptions
    async def execute_many(self, query: str, values: list) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            async with connection.cursor() as cursor:
                if self.capabilities.supports_transactions:
                    await connection.begin()
                    try:
                        await cursor.executemany(query, values)
                    except Exception:
                        await connection.rollback()
                        raise
                    else:
                        await connection.commit()
                else:
                    await cursor.executemany(query, values)

    async def execute_query_dict(self, query: str, values: Optional[list] = None) -> List[dict]:
        return (await self.execute_query(query, values))[1]
