import abc
from asyncio.events import AbstractEventLoop
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    List,
    Optional,
    SupportsInt,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from pypika import PostgreSQLQuery

from tortoise.backends.base.client import (
    BaseDBAsyncClient,
    Capabilities,
    ConnectionWrapper,
    PoolConnectionWrapper,
    TransactionContext,
)
from tortoise.backends.base_postgres.executor import BasePostgresExecutor
from tortoise.backends.base_postgres.schema_generator import BasePostgresSchemaGenerator

if TYPE_CHECKING:
    from asyncpg.connection import Connection
    from psycopg import AsyncConnection

T = TypeVar("T")
FuncType = Callable[..., Coroutine[None, None, T]]


def translate_exceptions(func: FuncType) -> FuncType:
    @wraps(func)
    async def _translate_exceptions(self, *args, **kwargs) -> T:
        return await self._translate_exceptions(func, *args, **kwargs)

    return _translate_exceptions


class BasePostgresPool:
    pass


class BasePostgresClient(BaseDBAsyncClient, abc.ABC):
    DSN_TEMPLATE = "postgres://{user}:{password}@{host}:{port}/{database}"
    query_class: Type[PostgreSQLQuery] = PostgreSQLQuery
    executor_class: Type[BasePostgresExecutor] = BasePostgresExecutor
    schema_generator: Type[BasePostgresSchemaGenerator] = BasePostgresSchemaGenerator
    capabilities = Capabilities("postgres", support_update_limit_order_by=False)
    connection_class: "Optional[Union[AsyncConnection, Connection]]" = None
    loop: Optional[AbstractEventLoop] = None
    _pool: Optional[Any] = None
    _connection: Optional[Any] = None

    def __init__(
        self,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
        host: Optional[str] = None,
        port: SupportsInt = 5432,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)

        self.user = user
        self.password = password
        self.database = database
        self.host = host
        self.port = int(port)  # make sure port is int type
        self.extra = kwargs.copy()
        # we can't deep copy kwargs because of ssl context
        # since server_settings is a dict, we copy it again
        self.server_settings = (self.extra.pop("server_settings", None) or {}).copy()
        self.schema = self.extra.pop("schema", None)
        self.application_name = self.extra.pop("application_name", None)
        self.extra.pop("connection_name", None)
        self.extra.pop("fetch_inserted", None)
        self.loop = self.extra.pop("loop", None)
        self.connection_class = self.extra.pop("connection_class", self.connection_class)
        self.pool_minsize = int(self.extra.pop("minsize", 1))
        self.pool_maxsize = int(self.extra.pop("maxsize", 5))

        self._template: dict = {}
        self._pool = None
        self._connection = None

    @abc.abstractmethod
    async def create_connection(self, with_db: bool) -> None:
        raise NotImplementedError("create_connection is not implemented")

    @abc.abstractmethod
    async def create_pool(self, **kwargs):
        raise NotImplementedError("create_pool is not implemented")

    @abc.abstractmethod
    async def _expire_connections(self) -> None:
        raise NotImplementedError("_expire_connections is not implemented")

    @abc.abstractmethod
    async def _close(self) -> None:
        raise NotImplementedError("_close is not implemented")

    @abc.abstractmethod
    async def _translate_exceptions(self, func, *args, **kwargs) -> Exception:
        raise NotImplementedError("translate_exceptions is not implemented")

    async def close(self) -> None:
        await self._close()
        self._template.clear()

    async def db_create(self) -> None:
        await self.create_connection(with_db=False)
        await self.execute_script(f'CREATE DATABASE "{self.database}" OWNER "{self.user}"')
        await self.close()

    async def db_delete(self) -> None:
        await self.create_connection(with_db=False)
        try:
            await self.execute_script(f'DROP DATABASE "{self.database}"')
        finally:
            await self.close()

    def acquire_connection(self) -> Union["ConnectionWrapper", "PoolConnectionWrapper"]:
        return PoolConnectionWrapper(self._pool)

    @abc.abstractmethod
    def _in_transaction(self) -> "TransactionContext":
        raise NotImplementedError("_in_transaction is not implemented")

    @abc.abstractmethod
    async def execute_insert(self, query: str, values: list) -> Optional[Any]:
        raise NotImplementedError("execute_insert is not implemented")

    @abc.abstractmethod
    async def execute_many(self, query: str, values: list) -> None:
        raise NotImplementedError("execute_many is not implemented")

    @abc.abstractmethod
    async def execute_query(
        self, query: str, values: Optional[list] = None
    ) -> Tuple[int, List[dict]]:
        raise NotImplementedError("execute_query is not implemented")

    @abc.abstractmethod
    async def execute_query_dict(self, query: str, values: Optional[list] = None) -> List[dict]:
        raise NotImplementedError("execute_query_dict is not implemented")

    @translate_exceptions
    async def execute_script(self, query: str) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug(query)
            await connection.execute(query)
