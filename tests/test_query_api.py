from __future__ import annotations

from typing import TypedDict, Union, cast

import pytest
import pytest_asyncio
from pydantic import BaseModel, TypeAdapter, ValidationError
from pypika_tortoise import Query, Table
from pypika_tortoise.context import SqlContext
from pypika_tortoise.queries import QueryBuilder
from pypika_tortoise.terms import Parameterizer
from typing_extensions import assert_type

from tests.testmodels import Tournament
from tortoise import fields
from tortoise.connection import connections
from tortoise.context import TortoiseContext, tortoise_test_context
from tortoise.contrib import test
from tortoise.exceptions import ParamsError
from tortoise.models import Model
from tortoise.query_api import QueryResult, execute_pypika


class QueryModel(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()


class QueryRow(BaseModel):
    id: int
    name: str


class QueryRowDict(TypedDict):
    id: int
    name: str


# =============================================================================
# Tests for TestQueryApi (formerly SimpleTestCase)
# Uses custom in-memory SQLite initialization
# =============================================================================


@pytest_asyncio.fixture
async def query_api_db():
    """Fixture for QueryApi tests that initializes an in-memory SQLite database."""
    async with tortoise_test_context(modules=[__name__]) as ctx:
        await QueryModel.create(id=1, name="alpha")
        await QueryModel.create(id=2, name="beta")
        yield ctx


@pytest.mark.asyncio
async def test_execute_pypika(query_api_db) -> None:
    table = QueryModel.get_table()
    query = Query.from_(table).select(table.id, table.name).where(table.name == "alpha")

    result: QueryResult[dict] = await execute_pypika(query)

    assert result.rows == [{"id": 1, "name": "alpha"}]
    assert result.rows_affected == 1


@pytest.mark.asyncio
async def test_execute_pypika_metadata(query_api_db) -> None:
    table = QueryModel.get_table()
    query = Query.from_(table).select(table.id, table.name)

    result: QueryResult[dict] = await execute_pypika(query)

    assert result.rows_affected == 2


@pytest.mark.asyncio
async def test_execute_pypika_update_rows_affected(query_api_db) -> None:
    table = QueryModel.get_table()
    query = Query.update(table).set(table.name, "gamma").where(table.id == 1)

    result: QueryResult[dict] = await execute_pypika(query)

    assert result.rows == []
    assert result.rows_affected == 1


@pytest.mark.asyncio
async def test_execute_pypika_insert_rows_affected(query_api_db) -> None:
    table = QueryModel.get_table()
    query = Query.into(table).columns(table.name).insert("delta")

    result: QueryResult[dict] = await execute_pypika(query)

    assert result.rows == []
    assert result.rows_affected == 1


@pytest.mark.asyncio
async def test_query_parameterization(query_api_db) -> None:
    table = QueryModel.get_table()
    query = Query.from_(table).select(table.id).where(table.name == "alpha")
    db = connections.get("default")

    sql, params = query.get_parameterized_sql(db.query_class.SQL_CONTEXT)

    assert "alpha" in params
    assert "alpha" not in sql


@pytest.mark.asyncio
async def test_execute_pypika_pydantic_schema(query_api_db) -> None:
    table = QueryModel.get_table()
    query = Query.from_(table).select(table.id, table.name).where(table.name == "alpha")

    result = cast(QueryResult[QueryRow], await execute_pypika(query, schema=QueryRow))

    assert isinstance(result.rows[0], QueryRow)
    assert result.rows[0].model_dump() == {"id": 1, "name": "alpha"}


@pytest.mark.asyncio
async def test_execute_pypika_pydantic_type_adapter(query_api_db) -> None:
    table = QueryModel.get_table()
    query = Query.from_(table).select(table.id, table.name).where(table.name == "alpha")
    adapter = TypeAdapter(dict[str, int | str])

    result: QueryResult[dict[str, Union[int, str]]] = await execute_pypika(  # noqa: UP007
        query,
        schema=adapter,
    )

    assert result.rows == [{"id": 1, "name": "alpha"}]


@pytest.mark.asyncio
async def test_execute_pypika_typed_dict_schema(query_api_db) -> None:
    table = QueryModel.get_table()
    query = Query.from_(table).select(table.id, table.name).where(table.name == "alpha")

    result: QueryResult[QueryRowDict] = await execute_pypika(query, schema=QueryRowDict)

    assert_type(result, QueryResult[QueryRowDict])
    assert_type(result.rows, list[QueryRowDict])
    assert result.rows == [{"id": 1, "name": "alpha"}]


@pytest.mark.asyncio
async def test_execute_pypika_empty_result(query_api_db) -> None:
    table = QueryModel.get_table()
    query = Query.from_(table).select(table.id, table.name).where(table.name == "missing")

    result: QueryResult[dict] = await execute_pypika(query)

    assert result.rows == []
    assert result.rows_affected == 0


@pytest.mark.asyncio
async def test_execute_pypika_invalid_schema_raises(query_api_db) -> None:
    table = QueryModel.get_table()
    query = Query.from_(table).select(table.name.as_("id"), table.name)

    with pytest.raises(ValidationError):
        await execute_pypika(query, schema=QueryRow)


# =============================================================================
# Tests for TestQueryApiRowsAffected (formerly test.TestCase)
# Uses db fixture with Tournament model
# =============================================================================


def _is_asyncpg(db) -> bool:
    return "tortoise.backends.asyncpg" in type(db.db()).__module__


def _is_psycopg(db) -> bool:
    return "tortoise.backends.psycopg" in type(db.db()).__module__


def _is_mysql(db) -> bool:
    return "tortoise.backends.mysql" in type(db.db()).__module__


def _is_odbc(db) -> bool:
    return "tortoise.backends.odbc" in type(db.db()).__module__


def _select_query() -> QueryBuilder:
    table = Tournament.get_table()
    return Query.from_(table).select(table.id, table.name).orderby(table.id)


def _sql_context(db) -> SqlContext:
    ctx = db.db().query_class.SQL_CONTEXT
    if _is_psycopg(db) and ctx.parameterizer is None:
        ctx = ctx.copy(parameterizer=Parameterizer(placeholder_factory=lambda _: "%s"))
    return ctx


@pytest_asyncio.fixture
async def rows_affected_setup(db):
    """Fixture to set up Tournament data for rows_affected tests."""
    alpha = await Tournament.create(name="alpha")
    beta = await Tournament.create(name="beta")
    return {"alpha_id": alpha.id, "beta_id": beta.id, "db": db}


@test.requireCapability(dialect="sqlite")
@pytest.mark.asyncio
async def test_rows_affected_select_sqlite(rows_affected_setup) -> None:
    result: QueryResult[dict] = await execute_pypika(_select_query())

    assert result.rows_affected == len(result.rows)
    assert len(result.rows) == 2


@test.requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_rows_affected_select_asyncpg(rows_affected_setup) -> None:
    db = rows_affected_setup["db"]
    if not _is_asyncpg(db):
        pytest.skip("asyncpg only")

    result: QueryResult[dict] = await execute_pypika(_select_query())

    assert result.rows_affected == len(result.rows)
    assert len(result.rows) == 2


@pytest.mark.asyncio
async def test_rows_affected_select_driver_rowcount(rows_affected_setup) -> None:
    db = rows_affected_setup["db"]
    if not (_is_mysql(db) or _is_odbc(db) or _is_psycopg(db)):
        pytest.skip("mysql/odbc/psycopg only")

    query: QueryBuilder = _select_query()
    sql, params = query.get_parameterized_sql(_sql_context(db))
    raw_rowcount, _ = await db.db().execute_query(sql, params)
    result: QueryResult[dict] = await execute_pypika(query)

    expected = {raw_rowcount, len(result.rows)}
    assert result.rows_affected in expected


@pytest.mark.asyncio
async def test_rows_affected_update(rows_affected_setup) -> None:
    alpha_id = rows_affected_setup["alpha_id"]
    table = Tournament.get_table()
    query = Query.update(table).set(table.name, "gamma").where(table.id == alpha_id)

    result: QueryResult[dict] = await execute_pypika(query)

    assert result.rows == []
    assert result.rows_affected == 1


@pytest.mark.asyncio
async def test_rows_affected_delete(rows_affected_setup) -> None:
    beta_id = rows_affected_setup["beta_id"]
    table = Tournament.get_table()
    query = Query.from_(table).delete().where(table.id == beta_id)

    result: QueryResult[dict] = await execute_pypika(query)

    assert result.rows == []
    assert result.rows_affected == 1


# =============================================================================
# Tests for TestQueryApiConnectionSelection (formerly SimpleTestCase)
# Tests connection selection behavior
# =============================================================================


@pytest.mark.asyncio
async def test_execute_pypika_explicit_connection_with_multiple_configured() -> None:
    """Test execute_pypika with explicit connection when multiple are configured."""

    class DummyClient:
        query_class = type("QueryClass", (), {"SQL_CONTEXT": None})

        async def execute_query_dict_with_affected(self, query, values=None):
            return [], 0

    async with TortoiseContext() as ctx:
        await ctx.init(
            config={
                "connections": {
                    "first": "sqlite://:memory:",
                    "second": "sqlite://:memory:",
                },
                "apps": {
                    "models": {"models": [__name__], "default_connection": "first"},
                },
            }
        )
        await ctx.generate_schemas()

        query = Query.from_(Table("dummy")).select("*")

        token = ctx.connections.set("second", DummyClient())  # type: ignore[arg-type]
        try:
            result: QueryResult[dict] = await execute_pypika(
                query, using_db=ctx.connections.get("second")
            )
        finally:
            ctx.connections.reset(token)

        assert result.rows_affected == 0


@pytest_asyncio.fixture
async def multi_db():
    """Fixture that sets up multiple databases for testing."""
    from tortoise.context import TortoiseContext

    ctx = TortoiseContext()
    async with ctx:
        await ctx.init(
            config={
                "connections": {
                    "first": "sqlite://:memory:",
                    "second": "sqlite://:memory:",
                },
                "apps": {
                    "models": {"models": [__name__], "default_connection": "first"},
                },
            }
        )
        await ctx.generate_schemas()
        yield ctx


@pytest.mark.asyncio
async def test_execute_pypika_requires_connection_with_multiple_configured(multi_db) -> None:
    query = Query.from_(Table("dummy")).select("*")

    with pytest.raises(ParamsError) as exc_info:
        await execute_pypika(query)

    assert "multiple databases" in str(exc_info.value)
