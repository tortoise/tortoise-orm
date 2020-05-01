import asyncio
from functools import wraps
from typing import Any, Callable, List, Optional, SupportsInt, Tuple, TypeVar, Union

import aioodbc
from pypika import Dialects
from pypika.queries import Query, QueryBuilder

import pyodbc
from tortoise.backends.aioodbc.executor import AioodbcExecutor
from tortoise.backends.aioodbc.schema_generator import AioodbcSchemaGenerator
from tortoise.backends.base.client import (
    BaseDBAsyncClient,
    BaseTransactionWrapper,
    Capabilities,
    ConnectionWrapper,
    NestedTransactionPooledContext,
    PoolConnectionWrapper,
    TransactionContext,
    TransactionContextPooled,
)
from tortoise.exceptions import (
    DBConnectionError,
    IntegrityError,
    OperationalError,
    TransactionManagementError,
)

FuncType = Callable[..., Any]
F = TypeVar("F", bound=FuncType)


def translate_exceptions(func: F) -> F:
    @wraps(func)
    async def translate_exceptions_(self, *args):
        try:
            return await func(self, *args)
        except pyodbc.ProgrammingError as exc:
            raise OperationalError(exc)
        except pyodbc.IntegrityError as exc:
            raise IntegrityError(exc)
        except pyodbc.Error as exc:
            tb = exc.__traceback__
            if exc.args[0] == "HY000":
                msg = list(exc.args[1])
                msg = msg[: int(len(msg) / 2 - 7)]
                msg = str("".join(msg))
            raise OperationalError(msg)

    return translate_exceptions_  # type: ignore


class OracleQueryBuilder(QueryBuilder):  # type: ignore
    def __init__(self, **kwargs):
        super(OracleQueryBuilder, self).__init__(dialect=Dialects.ORACLE, **kwargs)

    def get_sql(self, *args, **kwargs):
        return super(OracleQueryBuilder, self).get_sql(*args, groupby_alias=False, **kwargs)

    def _limit_sql(self):
        return f" FETCH NEXT {self._limit} ROWS ONLY"


class OracleQuery(Query):  # type: ignore
    """
    Defines a query class for use with Oracle.
    """

    @classmethod
    def _builder(cls, **kwargs):
        builder = OracleQueryBuilder(**kwargs)  # type: ignore
        builder.QUOTE_CHAR = '"'
        return builder


DSN_TEMPLATE = (
    "ODBC;"
    "Driver={{{driver}}};"
    "SERVER={c.host}:{c.port}"
    "/{c.database};"
    "UID={c.user};"
    "PWD={c.password}"
    ";SCHEMA={c.schema};"
)


class AioodbcDBClient(BaseDBAsyncClient):
    query_class = OracleQuery
    executor_class = AioodbcExecutor
    schema_generator = AioodbcSchemaGenerator
    capabilities = Capabilities("oracle")

    def __init__(
        self, user: str, password: str, database: str, host: str, port: SupportsInt, **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)

        self.user = user
        self.password = password
        self.database = database
        self.host = host
        self.port = int(port)  # make sure port is int type
        self.extra = kwargs.copy()
        self.schema = self.extra.pop("schema", None)
        self.extra.pop("connection_name", None)
        self.extra.pop("fetch_inserted", None)
        self.extra.pop("loop", None)
        self.extra.pop("connection_class", None)
        self.pool_minsize = int(self.extra.pop("minsize", 1))
        self.pool_maxsize = int(self.extra.pop("maxsize", 5))

        self._template: dict = {}
        self._pool: Optional[aioodbc.Pool] = None
        self._connection: Optional[aioodbc.Connection] = None

    async def create_connection(self, with_db: bool) -> None:
        self._template = {
            "server": self.host,
            "port": self.port,
            "uid": self.user,
            "database": self.database if with_db else None,
            "min_size": self.pool_minsize,
            "max_size": self.pool_maxsize,
            "pwd": self.password,
            **self.extra,
        }
        self._template["dsn"] = DSN_TEMPLATE.format(c=self, driver=self.extra["driver"])
        if self.schema:
            self._template["server_settings"] = {"search_path": self.schema}

        async def conn_attributes(conn):
            # conn.setdecoding(pyodbc.SQL_CHAR, encoding='utf-8')
            # conn.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-8')
            # conn.setdecoding(pyodbc.SQL_WMETADATA, encoding='utf-16le')
            # conn.setencoding(encoding='utf-16')
            pass

        try:
            self._pool = await aioodbc.create_pool(
                loop=None, **self._template, after_created=conn_attributes
            )
            self.log.debug("Created connection pool %s with params: %s", self._pool, self._template)
        except pyodbc.OperationalError:
            raise DBConnectionError(f"Can't establish connection to database {self.database}")
        # Set post-connection variables

    async def _expire_connections(self) -> None:
        if self._pool:  # pragma: nobranch
            await self._pool.expire_connections()

    async def _close(self) -> None:
        if self._pool:  # pragma: nobranch
            try:
                self._pool.close()
                await asyncio.wait_for(self._pool.wait_closed(), 10)
            except asyncio.TimeoutError:  # pragma: nocoverage
                self._pool.close()
            self._pool = None
            self.log.debug("Closed connection pool %s with params: %s", self._pool, self._template)

    async def close(self) -> None:
        await self._close()
        self._template.clear()

    async def db_create(self) -> None:
        query = """
            BEGIN
            FOR c IN (SELECT table_name FROM user_tables) LOOP
            EXECUTE IMMEDIATE ('DROP TABLE "' || c.table_name || '" CASCADE CONSTRAINTS');
            END LOOP;
            END; """
        await self.create_connection(with_db=True)
        try:
            await self.execute_script(query)
        except pyodbc.ProgrammingError:  # pragma: nocoverage
            pass
        await self.close()
        # await self.db_delete()
        # await self.create_connection(with_db=False)
        # await self.execute_script(f'CREATE DATABASE "{self.database}" OWNER "{self.user}"')
        # await self.close()

    async def db_delete(self) -> None:
        # query = """
        #    BEGIN
        #    FOR c IN (SELECT table_name FROM user_tables) LOOP
        #    EXECUTE IMMEDIATE ('DROP TABLE "' || c.table_name || '" CASCADE CONSTRAINTS');
        #    END LOOP;
        #    END; """
        # await self.create_connection(with_db=True)
        # try:
        #    await self.execute_script(query)
        # except pyodbc.ProgrammingError:  # pragma: nocoverage
        #    pass
        # await self.close()
        pass

    def acquire_connection(self) -> Union["PoolConnectionWrapper", "ConnectionWrapper"]:
        return PoolConnectionWrapper(self._pool)

    def _in_transaction(self) -> "TransactionContext":
        return TransactionContextPooled(TransactionWrapper(self))

    @translate_exceptions
    async def execute_insert(self, query: str, values: list):
        """ Execute insert and get returned ID if autogenerated. 
        Currently has to hack around Oracle's autonumer not returning last
        last inserted ID by default"""
        # TODO: If we are keeping the hack around at least get the sequence pointer only once
        # and store it in the table. From there have the OracleQueryBuilder build inserts with
        # currval already requested.

        # Parse table from query. (INSERT INTO "TABLE"...)
        table = query.split()[2].replace('"', "'")
        data_default_query = f"""
            SELECT DATA_DEFAULT FROM USER_TAB_COLUMNS 
            WHERE TABLE_NAME = {table} AND DATA_DEFAULT IS NOT NULL"""
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)

            async with connection.cursor() as crsr:
                # Get sequence pointer for table.
                await crsr.execute(data_default_query)
                res = (await crsr.fetchone())[0]
                seq_pointer = res.split(".")[1]

                # Actual insertion.
                params = [item for item in [query, values] if item]
                logging.debug(params)
                await crsr.execute(*params)

                # Get current value of sequence post insertion.
                currval_query = f"SELECT {seq_pointer}.currval FROM dual;"
                await crsr.execute(currval_query)
                return (await crsr.fetchone())[0]

    #    @translate_exceptions
    #    async def execute_many(self, query: str, values: list) -> None:
    #        async with self.acquire_connection() as cnxn:
    #            autocommit_orig = cnxn.autocommit
    #            cnxn.autocommit = False
    #            async with cnxn.cursor() as crsr:
    #                self.log.debug("%s: %s", query, values)
    #                try:
    #                    # Possibly useful for speedups.
    #                    # crsr.fast_executemany = True
    #                    await crsr.executemany(query, values)
    #                except pyodbc.DatabaseError:
    #                    cnxn.rollback()
    #                else:
    #                    cnxn.commit()
    #                finally:
    #                    cnxn.autocommit = autocommit_orig

    @translate_exceptions
    async def execute_query(
        self, query: str, values: Optional[list] = None
    ) -> Tuple[int, List[dict]]:
        print("#" * 30)
        print(query)
        print("#" * 30)
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            async with connection.cursor() as crsr:
                params = [item for item in [query, values] if item]
                await crsr.execute(*params)
                if "UPDATE" in query:
                    return 1, []
                rows = await crsr.fetchall()
                if rows:
                    fields = [f[0].lower() for f in crsr.description]
                    return crsr.rowcount, [dict(zip(fields, row)) for row in rows]
                return crsr.rowcount, []

    async def execute_query_dict(self, query: str, values: Optional[list] = None) -> List[dict]:
        return (await self.execute_query(query, values))[1]

    @translate_exceptions
    async def execute_script(self, query: str) -> None:
        logging.debug("Executing script: ".format(query))
        # queries = query.split(';')
        # queries = [query for query in queries if query]
        # for query in queries:
        #    query = query + ';'
        print("#" * 30)
        print(query)
        print("#" * 30)
        async with self.acquire_connection() as connection:
            async with connection.cursor() as crsr:
                self.log.debug(query)
                await crsr.execute(query)


class TransactionWrapper(AioodbcDBClient, BaseTransactionWrapper):
    def __init__(self, connection: AioodbcDBClient) -> None:
        self.connection_name = connection.connection_name
        self._connection: aioodbc.Connection = connection._connection
        self._lock = asyncio.Lock()
        self._trxlock = asyncio.Lock()
        self.log = connection.log
        self._finalized: Optional[bool] = None
        self._parent = connection
        self._autocommit_orig = None

    def _in_transaction(self) -> "TransactionContext":
        return NestedTransactionPooledContext(self)

    def acquire_connection(self) -> ConnectionWrapper:
        return ConnectionWrapper(self._connection, self._lock)

    #    @translate_exceptions
    #    async def execute_many(self, query: str, values: list) -> None:
    #        async with self.acquire_connection() as cnxn:
    #            self._autocommit_orig = cnxn.autocommit
    #            cnxn.autocommit = False
    #            async with cnxn.cursor() as crsr:
    #                self.log.debug("%s: %s", query, values)
    #                await crsr.executemany(query, values)

    @translate_exceptions
    async def start(self) -> None:
        self._finalized = False

    async def commit(self) -> None:
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        await self._connection.commit()
        self._connection.autocommit = self._autocommit_orig
        self._finalized = True

    async def rollback(self) -> None:
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        await self._connection.rollback()
        self._finalized = True
