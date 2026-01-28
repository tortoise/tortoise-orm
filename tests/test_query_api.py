from __future__ import annotations

from typing import TypedDict, Union, cast

from pydantic import BaseModel, TypeAdapter, ValidationError
from pypika_tortoise import Query, Table
from pypika_tortoise.context import SqlContext
from pypika_tortoise.queries import QueryBuilder
from pypika_tortoise.terms import Parameterizer
from typing_extensions import assert_type

from tests.testmodels import Tournament
from tortoise import Tortoise, fields
from tortoise.connection import connections
from tortoise.contrib import test
from tortoise.contrib.test import SimpleTestCase
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


class TestQueryApi(SimpleTestCase):
    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": [__name__]})
        await Tortoise.generate_schemas()
        await QueryModel.create(id=1, name="alpha")
        await QueryModel.create(id=2, name="beta")

    async def _tearDownDB(self) -> None:
        await Tortoise.get_connection("default").close()

    async def test_execute_pypika(self) -> None:
        table = QueryModel.get_table()
        query = Query.from_(table).select(table.id, table.name).where(table.name == "alpha")

        result: QueryResult[dict] = await execute_pypika(query)

        self.assertEqual(result.rows, [{"id": 1, "name": "alpha"}])
        self.assertEqual(result.rows_affected, 1)

    async def test_execute_pypika_metadata(self) -> None:
        table = QueryModel.get_table()
        query = Query.from_(table).select(table.id, table.name)

        result: QueryResult[dict] = await execute_pypika(query)

        self.assertEqual(result.rows_affected, 2)

    async def test_execute_pypika_update_rows_affected(self) -> None:
        table = QueryModel.get_table()
        query = Query.update(table).set(table.name, "gamma").where(table.id == 1)

        result: QueryResult[dict] = await execute_pypika(query)

        self.assertEqual(result.rows, [])
        self.assertEqual(result.rows_affected, 1)

    async def test_execute_pypika_insert_rows_affected(self) -> None:
        table = QueryModel.get_table()
        query = Query.into(table).columns(table.name).insert("delta")

        result: QueryResult[dict] = await execute_pypika(query)

        self.assertEqual(result.rows, [])
        self.assertEqual(result.rows_affected, 1)

    async def test_query_parameterization(self) -> None:
        table = QueryModel.get_table()
        query = Query.from_(table).select(table.id).where(table.name == "alpha")
        db = connections.get("default")

        sql, params = query.get_parameterized_sql(db.query_class.SQL_CONTEXT)

        self.assertIn("alpha", params)
        self.assertNotIn("alpha", sql)

    async def test_execute_pypika_pydantic_schema(self) -> None:
        table = QueryModel.get_table()
        query = Query.from_(table).select(table.id, table.name).where(table.name == "alpha")

        result = cast(QueryResult[QueryRow], await execute_pypika(query, schema=QueryRow))

        self.assertIsInstance(result.rows[0], QueryRow)
        self.assertEqual(result.rows[0].model_dump(), {"id": 1, "name": "alpha"})

    async def test_execute_pypika_pydantic_type_adapter(self) -> None:
        table = QueryModel.get_table()
        query = Query.from_(table).select(table.id, table.name).where(table.name == "alpha")
        adapter = TypeAdapter(dict[str, int | str])

        result: QueryResult[dict[str, Union[int, str]]] = await execute_pypika(  # noqa: UP007
            query,
            schema=adapter,
        )

        self.assertEqual(result.rows, [{"id": 1, "name": "alpha"}])

    async def test_execute_pypika_typed_dict_schema(self) -> None:
        table = QueryModel.get_table()
        query = Query.from_(table).select(table.id, table.name).where(table.name == "alpha")

        result: QueryResult[QueryRowDict] = await execute_pypika(query, schema=QueryRowDict)

        assert_type(result, QueryResult[QueryRowDict])
        assert_type(result.rows, list[QueryRowDict])
        self.assertEqual(result.rows, [{"id": 1, "name": "alpha"}])

    async def test_execute_pypika_empty_result(self) -> None:
        table = QueryModel.get_table()
        query = Query.from_(table).select(table.id, table.name).where(table.name == "missing")

        result: QueryResult[dict] = await execute_pypika(query)

        self.assertEqual(result.rows, [])
        self.assertEqual(result.rows_affected, 0)

    async def test_execute_pypika_invalid_schema_raises(self) -> None:
        table = QueryModel.get_table()
        query = Query.from_(table).select(table.name.as_("id"), table.name)

        with self.assertRaises(ValidationError):
            await execute_pypika(query, schema=QueryRow)


class TestQueryApiRowsAffected(test.TestCase):
    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        alpha = await Tournament.create(name="alpha")
        beta = await Tournament.create(name="beta")
        self._alpha_id = alpha.id
        self._beta_id = beta.id

    def _is_asyncpg(self) -> bool:
        return "tortoise.backends.asyncpg" in type(self._db).__module__

    def _is_psycopg(self) -> bool:
        return "tortoise.backends.psycopg" in type(self._db).__module__

    def _is_mysql(self) -> bool:
        return "tortoise.backends.mysql" in type(self._db).__module__

    def _is_odbc(self) -> bool:
        return "tortoise.backends.odbc" in type(self._db).__module__

    def _select_query(self) -> QueryBuilder:
        table = Tournament.get_table()
        return Query.from_(table).select(table.id, table.name).orderby(table.id)

    def _sql_context(self) -> SqlContext:
        ctx = self._db.query_class.SQL_CONTEXT
        if self._is_psycopg() and ctx.parameterizer is None:
            ctx = ctx.copy(parameterizer=Parameterizer(placeholder_factory=lambda _: "%s"))
        return ctx

    @test.requireCapability(dialect="sqlite")
    async def test_rows_affected_select_sqlite(self) -> None:
        result: QueryResult[dict] = await execute_pypika(self._select_query())

        self.assertEqual(result.rows_affected, len(result.rows))
        self.assertEqual(len(result.rows), 2)

    @test.requireCapability(dialect="postgres")
    async def test_rows_affected_select_asyncpg(self) -> None:
        if not self._is_asyncpg():
            self.skipTest("asyncpg only")

        result: QueryResult[dict] = await execute_pypika(self._select_query())

        self.assertEqual(result.rows_affected, len(result.rows))
        self.assertEqual(len(result.rows), 2)

    async def test_rows_affected_select_driver_rowcount(self) -> None:
        if not (self._is_mysql() or self._is_odbc() or self._is_psycopg()):
            self.skipTest("mysql/odbc/psycopg only")

        query: QueryBuilder = self._select_query()
        sql, params = query.get_parameterized_sql(self._sql_context())
        raw_rowcount, _ = await self._db.execute_query(sql, params)
        result: QueryResult[dict] = await execute_pypika(query)

        expected = {raw_rowcount, len(result.rows)}
        self.assertIn(result.rows_affected, expected)

    async def test_rows_affected_update(self) -> None:
        table = Tournament.get_table()
        query = Query.update(table).set(table.name, "gamma").where(table.id == self._alpha_id)

        result: QueryResult[dict] = await execute_pypika(query)

        self.assertEqual(result.rows, [])
        self.assertEqual(result.rows_affected, 1)

    async def test_rows_affected_delete(self) -> None:
        table = Tournament.get_table()
        query = Query.from_(table).delete().where(table.id == self._beta_id)

        result: QueryResult[dict] = await execute_pypika(query)

        self.assertEqual(result.rows, [])
        self.assertEqual(result.rows_affected, 1)


class TestQueryApiConnectionSelection(SimpleTestCase):
    async def test_execute_pypika_explicit_connection_with_multiple_configured(self) -> None:
        connections._db_config = {"first": {}, "second": {}}
        query = Query.from_(Table("dummy")).select("*")

        class DummyClient:
            query_class = type("QueryClass", (), {"SQL_CONTEXT": None})

            async def execute_query_dict_with_affected(self, query, values=None):
                return [], 0

        token = connections.set("second", DummyClient())  # type: ignore[arg-type]
        try:
            result: QueryResult[dict] = await execute_pypika(
                query, using_db=connections.get("second")
            )
        finally:
            connections.reset(token)

        self.assertEqual(result.rows_affected, 0)

    async def test_execute_pypika_requires_connection_with_multiple_configured(self) -> None:
        connections._db_config = {"first": {}, "second": {}}
        query = Query.from_(Table("dummy")).select("*")

        with self.assertRaises(ParamsError) as ctx:
            await execute_pypika(query)

        self.assertIn("multiple databases", str(ctx.exception))
