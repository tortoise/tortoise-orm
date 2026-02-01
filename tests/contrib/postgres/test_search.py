import os

from tests.contrib.postgres.models_tsvector import TSVectorEntry
from tests.testmodels import TextFields
from tortoise import connections
from tortoise.backends.psycopg.client import PsycopgClient
from tortoise.contrib import test
from tortoise.contrib.postgres.search import (
    Lexeme,
    SearchHeadline,
    SearchQuery,
    SearchRank,
    SearchVector,
)


class TestPostgresSearchExpressions(test.TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.db = connections.get("models")
        self.is_psycopg = isinstance(self.db, PsycopgClient)

    def assertSql(self, sql: str, expected_psycopg: str, expected_asyncpg: str) -> None:
        expected = expected_psycopg if self.is_psycopg else expected_asyncpg
        self.assertEqual(sql, expected)

    @test.requireCapability(dialect="postgres")
    def test_search_vector(self):
        sql = TextFields.all().annotate(search=SearchVector("text")).values("search").sql()
        self.assertSql(
            sql,
            'SELECT TO_TSVECTOR("text") "search" FROM "textfields"',
            'SELECT TO_TSVECTOR("text") "search" FROM "textfields"',
        )

    @test.requireCapability(dialect="postgres")
    def test_search_vector_config_weight(self):
        sql = (
            TextFields.all()
            .annotate(search=SearchVector("text", config="english", weight="A"))
            .values("search")
            .sql()
        )
        self.assertSql(
            sql,
            'SELECT SETWEIGHT(TO_TSVECTOR(%s,"text"),%s) "search" FROM "textfields"',
            'SELECT SETWEIGHT(TO_TSVECTOR($1,"text"),$2) "search" FROM "textfields"',
        )

    @test.requireCapability(dialect="postgres")
    def test_search_query_types(self):
        sql = (
            TextFields.all()
            .annotate(query=SearchQuery("fat", search_type="phrase"))
            .values("query")
            .sql()
        )
        self.assertSql(
            sql,
            'SELECT PHRASETO_TSQUERY(%s) "query" FROM "textfields"',
            'SELECT PHRASETO_TSQUERY($1) "query" FROM "textfields"',
        )

    @test.requireCapability(dialect="postgres")
    def test_search_query_combine_and_invert(self):
        query = SearchQuery("fat") & SearchQuery("rat")
        sql = TextFields.all().annotate(query=query).values("query").sql()
        self.assertSql(
            sql,
            'SELECT (PLAINTO_TSQUERY(%s) && PLAINTO_TSQUERY(%s)) "query" FROM "textfields"',
            'SELECT (PLAINTO_TSQUERY($1) && PLAINTO_TSQUERY($2)) "query" FROM "textfields"',
        )

        sql = TextFields.all().annotate(query=SearchQuery("fat", invert=True)).values("query").sql()
        self.assertSql(
            sql,
            'SELECT !!(PLAINTO_TSQUERY(%s)) "query" FROM "textfields"',
            'SELECT !!(PLAINTO_TSQUERY($1)) "query" FROM "textfields"',
        )

    @test.requireCapability(dialect="postgres")
    def test_search_query_lexeme(self):
        lexeme_query = SearchQuery(Lexeme("fat") & Lexeme("rat"))
        sql = TextFields.all().annotate(query=lexeme_query).values("query").sql()
        self.assertSql(
            sql,
            'SELECT TO_TSQUERY(%s) "query" FROM "textfields"',
            'SELECT TO_TSQUERY($1) "query" FROM "textfields"',
        )

    @test.requireCapability(dialect="postgres")
    def test_search_rank(self):
        sql = (
            TextFields.all()
            .annotate(rank=SearchRank(SearchVector("text"), SearchQuery("fat")))
            .values("rank")
            .sql()
        )
        self.assertSql(
            sql,
            'SELECT TS_RANK(TO_TSVECTOR("text"),PLAINTO_TSQUERY(%s)) "rank" FROM "textfields"',
            'SELECT TS_RANK(TO_TSVECTOR("text"),PLAINTO_TSQUERY($1)) "rank" FROM "textfields"',
        )

    @test.requireCapability(dialect="postgres")
    def test_search_headline(self):
        sql = (
            TextFields.all()
            .annotate(
                headline=SearchHeadline(
                    "text",
                    SearchQuery("fat"),
                    start_sel="<b>",
                    stop_sel="</b>",
                )
            )
            .values("headline")
            .sql()
        )
        self.assertSql(
            sql,
            'SELECT TS_HEADLINE("text",PLAINTO_TSQUERY(%s),%s) "headline" FROM "textfields"',
            'SELECT TS_HEADLINE("text",PLAINTO_TSQUERY($1),$2) "headline" FROM "textfields"',
        )

    @test.requireCapability(dialect="postgres")
    def test_search_lookup_text(self):
        sql = TextFields.filter(text__search="fat").values("id").sql()
        self.assertSql(
            sql,
            'SELECT "id" "id" FROM "textfields" WHERE TO_TSVECTOR("text") @@ PLAINTO_TSQUERY(%s)',
            'SELECT "id" "id" FROM "textfields" WHERE TO_TSVECTOR("text") @@ PLAINTO_TSQUERY($1)',
        )

    @test.requireCapability(dialect="postgres")
    def test_search_lookup_text_searchquery(self):
        sql = (
            TextFields.filter(text__search=SearchQuery("fat", search_type="raw")).values("id").sql()
        )
        self.assertSql(
            sql,
            'SELECT "id" "id" FROM "textfields" WHERE TO_TSVECTOR("text") @@ TO_TSQUERY(%s)',
            'SELECT "id" "id" FROM "textfields" WHERE TO_TSVECTOR("text") @@ TO_TSQUERY($1)',
        )


class TestPostgresSearchLookupTSVector(test.IsolatedTestCase):
    tortoise_test_modules = ["tests.contrib.postgres.models_tsvector"]

    async def asyncSetUp(self):
        db_url = os.getenv("TORTOISE_TEST_DB", "")
        if db_url.split(":", 1)[0] not in {"postgres", "asyncpg", "psycopg"}:
            raise test.SkipTest("Postgres-only test.")
        await super().asyncSetUp()
        self.db = connections.get("models")
        self.is_psycopg = isinstance(self.db, PsycopgClient)

    def assertSql(self, sql: str, expected_psycopg: str, expected_asyncpg: str) -> None:
        expected = expected_psycopg if self.is_psycopg else expected_asyncpg
        self.assertEqual(sql, expected)

    @test.requireCapability(dialect="postgres")
    def test_search_lookup_tsvector(self):
        sql = TSVectorEntry.filter(search_vector__search="fat").values("id").sql()
        self.assertSql(
            sql,
            'SELECT "id" "id" FROM "tsvector_entry" WHERE "search_vector" @@ PLAINTO_TSQUERY(%s)',
            'SELECT "id" "id" FROM "tsvector_entry" WHERE "search_vector" @@ PLAINTO_TSQUERY($1)',
        )

    @test.requireCapability(dialect="postgres")
    def test_search_lookup_tsvector_searchquery(self):
        sql = (
            TSVectorEntry.filter(search_vector__search=SearchQuery("fat", search_type="raw"))
            .values("id")
            .sql()
        )
        self.assertSql(
            sql,
            'SELECT "id" "id" FROM "tsvector_entry" WHERE "search_vector" @@ TO_TSQUERY(%s)',
            'SELECT "id" "id" FROM "tsvector_entry" WHERE "search_vector" @@ TO_TSQUERY($1)',
        )
