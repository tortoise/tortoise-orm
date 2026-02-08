import os

import pytest

from tests.contrib.postgres.models_tsvector import TSVectorEntry


def skip_if_not_postgres():
    """Skip test if not running against PostgreSQL."""
    db_url = os.getenv("TORTOISE_TEST_DB", "")
    if db_url.split(":", 1)[0] not in {"postgres", "asyncpg", "psycopg"}:
        pytest.skip("Postgres-only test.")


@pytest.mark.asyncio
async def test_tsvector_generated_sql(db_tsvector):
    """Test TSVector field generates correct SQL."""
    skip_if_not_postgres()
    field = TSVectorEntry._meta.fields_map["search_vector"]
    sql = field.get_for_dialect("postgres", "GENERATED_SQL")
    assert sql == (
        "GENERATED ALWAYS AS (SETWEIGHT(TO_TSVECTOR('english',COALESCE(\"title\", '')),'A')"
        " || SETWEIGHT(TO_TSVECTOR('english',COALESCE(\"body\", '')),'B')) STORED"
    )
