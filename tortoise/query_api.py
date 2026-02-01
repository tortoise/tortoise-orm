from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast, overload

from pypika_tortoise.queries import QueryBuilder
from pypika_tortoise.terms import Parameterizer

from tortoise.backends.base.client import BaseDBAsyncClient
from tortoise.connection import connections
from tortoise.exceptions import ParamsError

if TYPE_CHECKING:
    from pydantic import BaseModel as PydanticBaseModel
    from pydantic import TypeAdapter as PydanticTypeAdapter

    from tortoise.backends.psycopg.client import PsycopgClient

try:
    from pydantic import BaseModel as PydanticBaseModel
    from pydantic import TypeAdapter as PydanticTypeAdapter

    _PydanticBaseModel: type[PydanticBaseModel] | None = PydanticBaseModel
    _PydanticTypeAdapter: type[PydanticTypeAdapter] | None = PydanticTypeAdapter
    _PYDANTIC_AVAILABLE = True
except Exception:  # pragma: nocoverage
    _PydanticBaseModel = None
    _PydanticTypeAdapter = None
    _PYDANTIC_AVAILABLE = False

_PsycopgClient: type[PsycopgClient] | None
try:
    from tortoise.backends.psycopg.client import PsycopgClient as _PsycopgClient
except Exception:  # pragma: nocoverage
    _PsycopgClient = None

SchemaT = TypeVar("SchemaT")


@dataclass(frozen=True)
class QueryResult(Generic[SchemaT]):
    rows: list[SchemaT]
    rows_affected: int
    """
    Row count semantics depend on the backend and the query type:
    - SQLite: for SELECT, computed as the number of rows fetched; for UPDATE/DELETE,
      computed as the delta of total changes.
    - asyncpg: for SELECT, computed as the number of rows fetched; for UPDATE/DELETE,
      parsed from the driver's command status.
    - MySQL/ODBC/psycopg: typically uses cursor.rowcount for all queries. Note that for
      some drivers or statement types (e.g., SELECT), rowcount can be driver-defined.
    """


@overload
async def execute_pypika(
    query: QueryBuilder,
    *,
    using_db: BaseDBAsyncClient | None = None,
    schema: None = None,
) -> QueryResult[dict]: ...


@overload
async def execute_pypika(
    query: QueryBuilder,
    *,
    using_db: BaseDBAsyncClient | None = None,
    schema: type[SchemaT],
) -> QueryResult[SchemaT]: ...


@overload
async def execute_pypika(
    query: QueryBuilder,
    *,
    using_db: BaseDBAsyncClient | None = None,
    schema: PydanticTypeAdapter[SchemaT],
) -> QueryResult[SchemaT]: ...


async def execute_pypika(
    query: QueryBuilder,
    *,
    using_db: BaseDBAsyncClient | None = None,
    schema: type[SchemaT] | PydanticTypeAdapter[SchemaT] | Any | None = None,
) -> QueryResult[SchemaT] | QueryResult[dict]:
    if using_db is not None:
        db = using_db
    elif len(connections.db_config) == 1:
        connection_name = next(iter(connections.db_config.keys()))
        db = connections.get(connection_name)
    else:
        raise ParamsError(
            "You are running with multiple databases, so you should specify"
            f" connection_name: {list(connections.db_config)}"
        )
    sql, params = query.get_parameterized_sql(_get_sql_context(db))
    rows, rows_affected = await db.execute_query_dict_with_affected(sql, params)

    if schema is not None:
        rows = _validate_rows(rows, schema)

    return QueryResult(rows=rows, rows_affected=rows_affected)


def _get_sql_context(db: BaseDBAsyncClient):
    ctx = db.query_class.SQL_CONTEXT
    if _PsycopgClient is not None and isinstance(db, _PsycopgClient) and ctx.parameterizer is None:
        ctx = ctx.copy(parameterizer=Parameterizer(placeholder_factory=lambda _: "%s"))
    return ctx


def _validate_rows(rows: list[dict], schema: type[SchemaT] | Any) -> list[SchemaT]:
    if not _PYDANTIC_AVAILABLE:
        return cast(list[SchemaT], rows)

    if _PydanticTypeAdapter is not None and isinstance(schema, _PydanticTypeAdapter):
        return [cast(SchemaT, schema.validate_python(row)) for row in rows]

    if (
        _PydanticBaseModel is not None
        and isinstance(schema, type)
        and issubclass(schema, _PydanticBaseModel)
    ):
        return [cast(SchemaT, schema.model_validate(row)) for row in rows]

    return cast(list[SchemaT], rows)
