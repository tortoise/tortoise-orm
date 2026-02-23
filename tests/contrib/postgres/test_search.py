import os

import pytest

from tests.contrib.postgres.models_tsvector import TSVectorEntry
from tests.testmodels import TextFields
from tortoise import connections
from tortoise.backends.psycopg.client import PsycopgClient
from tortoise.contrib.postgres.search import (
    Lexeme,
    SearchHeadline,
    SearchQuery,
    SearchRank,
    SearchVector,
)
from tortoise.contrib.test import requireCapability


def skip_if_not_postgres():
    """Skip test if not running against PostgreSQL."""
    db_url = os.getenv("TORTOISE_TEST_DB", "")
    if db_url.split(":", 1)[0] not in {"postgres", "asyncpg", "psycopg"}:
        pytest.skip("Postgres-only test.")


def assert_sql(db, sql: str, expected_psycopg: str, expected_asyncpg: str) -> None:
    """Assert SQL matches expected value based on db client type."""
    is_psycopg = isinstance(db, PsycopgClient)
    expected = expected_psycopg if is_psycopg else expected_asyncpg
    assert sql == expected


# =============================================================================
# TestPostgresSearchExpressions - uses standard testmodels (test.TestCase equivalent)
# =============================================================================


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_search_vector(db_postgres):
    """Test SearchVector expression."""
    db = connections.get("models")
    sql = TextFields.all().annotate(search=SearchVector("text")).values("search").sql()
    assert_sql(
        db,
        sql,
        'SELECT TO_TSVECTOR("text") "search" FROM "textfields"',
        'SELECT TO_TSVECTOR("text") "search" FROM "textfields"',
    )


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_search_vector_config_weight(db_postgres):
    """Test SearchVector with config and weight."""
    db = connections.get("models")
    sql = (
        TextFields.all()
        .annotate(search=SearchVector("text", config="english", weight="A"))
        .values("search")
        .sql()
    )
    assert_sql(
        db,
        sql,
        'SELECT SETWEIGHT(TO_TSVECTOR(%s,"text"),%s) "search" FROM "textfields"',
        'SELECT SETWEIGHT(TO_TSVECTOR($1,"text"),$2) "search" FROM "textfields"',
    )


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_search_query_types(db_postgres):
    """Test SearchQuery with different search types."""
    db = connections.get("models")
    sql = (
        TextFields.all()
        .annotate(query=SearchQuery("fat", search_type="phrase"))
        .values("query")
        .sql()
    )
    assert_sql(
        db,
        sql,
        'SELECT PHRASETO_TSQUERY(%s) "query" FROM "textfields"',
        'SELECT PHRASETO_TSQUERY($1) "query" FROM "textfields"',
    )


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_search_query_combine_and_invert(db_postgres):
    """Test SearchQuery combine and invert operations."""
    db = connections.get("models")
    query = SearchQuery("fat") & SearchQuery("rat")
    sql = TextFields.all().annotate(query=query).values("query").sql()
    assert_sql(
        db,
        sql,
        'SELECT (PLAINTO_TSQUERY(%s) && PLAINTO_TSQUERY(%s)) "query" FROM "textfields"',
        'SELECT (PLAINTO_TSQUERY($1) && PLAINTO_TSQUERY($2)) "query" FROM "textfields"',
    )

    sql = TextFields.all().annotate(query=SearchQuery("fat", invert=True)).values("query").sql()
    assert_sql(
        db,
        sql,
        'SELECT !!(PLAINTO_TSQUERY(%s)) "query" FROM "textfields"',
        'SELECT !!(PLAINTO_TSQUERY($1)) "query" FROM "textfields"',
    )


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_search_query_lexeme(db_postgres):
    """Test SearchQuery with Lexeme."""
    db = connections.get("models")
    lexeme_query = SearchQuery(Lexeme("fat") & Lexeme("rat"))
    sql = TextFields.all().annotate(query=lexeme_query).values("query").sql()
    assert_sql(
        db,
        sql,
        'SELECT TO_TSQUERY(%s) "query" FROM "textfields"',
        'SELECT TO_TSQUERY($1) "query" FROM "textfields"',
    )


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_search_rank(db_postgres):
    """Test SearchRank expression."""
    db = connections.get("models")
    sql = (
        TextFields.all()
        .annotate(rank=SearchRank(SearchVector("text"), SearchQuery("fat")))
        .values("rank")
        .sql()
    )
    assert_sql(
        db,
        sql,
        'SELECT TS_RANK(TO_TSVECTOR("text"),PLAINTO_TSQUERY(%s)) "rank" FROM "textfields"',
        'SELECT TS_RANK(TO_TSVECTOR("text"),PLAINTO_TSQUERY($1)) "rank" FROM "textfields"',
    )


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_search_headline(db_postgres):
    """Test SearchHeadline expression."""
    db = connections.get("models")
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
    assert_sql(
        db,
        sql,
        'SELECT TS_HEADLINE("text",PLAINTO_TSQUERY(%s),%s) "headline" FROM "textfields"',
        'SELECT TS_HEADLINE("text",PLAINTO_TSQUERY($1),$2) "headline" FROM "textfields"',
    )


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_search_lookup_text(db_postgres):
    """Test search lookup on text field."""
    db = connections.get("models")
    sql = TextFields.filter(text__search="fat").values("id").sql()
    assert_sql(
        db,
        sql,
        'SELECT "id" "id" FROM "textfields" WHERE TO_TSVECTOR("text") @@ PLAINTO_TSQUERY(%s)',
        'SELECT "id" "id" FROM "textfields" WHERE TO_TSVECTOR("text") @@ PLAINTO_TSQUERY($1)',
    )


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_search_lookup_text_searchquery(db_postgres):
    """Test search lookup with SearchQuery on text field."""
    db = connections.get("models")
    sql = TextFields.filter(text__search=SearchQuery("fat", search_type="raw")).values("id").sql()
    assert_sql(
        db,
        sql,
        'SELECT "id" "id" FROM "textfields" WHERE TO_TSVECTOR("text") @@ TO_TSQUERY(%s)',
        'SELECT "id" "id" FROM "textfields" WHERE TO_TSVECTOR("text") @@ TO_TSQUERY($1)',
    )


# =============================================================================
# TestPostgresSearchLookupTSVector - uses TSVector models (IsolatedTestCase equivalent)
# =============================================================================


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_search_lookup_tsvector(db_search):
    """Test search lookup on TSVector field."""
    skip_if_not_postgres()
    db = connections.get("models")
    sql = TSVectorEntry.filter(search_vector__search="fat").values("id").sql()
    assert_sql(
        db,
        sql,
        'SELECT "id" "id" FROM "tsvector_entry" WHERE "search_vector" @@ PLAINTO_TSQUERY(%s)',
        'SELECT "id" "id" FROM "tsvector_entry" WHERE "search_vector" @@ PLAINTO_TSQUERY($1)',
    )


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_search_lookup_tsvector_searchquery(db_search):
    """Test search lookup with SearchQuery on TSVector field."""
    skip_if_not_postgres()
    db = connections.get("models")
    sql = (
        TSVectorEntry.filter(search_vector__search=SearchQuery("fat", search_type="raw"))
        .values("id")
        .sql()
    )
    assert_sql(
        db,
        sql,
        'SELECT "id" "id" FROM "tsvector_entry" WHERE "search_vector" @@ TO_TSQUERY(%s)',
        'SELECT "id" "id" FROM "tsvector_entry" WHERE "search_vector" @@ TO_TSQUERY($1)',
    )
