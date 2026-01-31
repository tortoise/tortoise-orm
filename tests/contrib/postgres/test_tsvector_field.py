import os

from tests.contrib.postgres.models_tsvector import TSVectorEntry
from tortoise.contrib import test


class TestTSVectorField(test.IsolatedTestCase):
    tortoise_test_modules = ["tests.contrib.postgres.models_tsvector"]

    async def asyncSetUp(self) -> None:
        db_url = os.getenv("TORTOISE_TEST_DB", "")
        if db_url.split(":", 1)[0] not in {"postgres", "asyncpg", "psycopg"}:
            raise test.SkipTest("Postgres-only test.")
        await super().asyncSetUp()

    def test_tsvector_generated_sql(self) -> None:
        field = TSVectorEntry._meta.fields_map["search_vector"]
        sql = field.get_for_dialect("postgres", "GENERATED_SQL")
        self.assertEqual(
            sql,
            "GENERATED ALWAYS AS (SETWEIGHT(TO_TSVECTOR('english',COALESCE(\"title\", '')),'A')"
            " || SETWEIGHT(TO_TSVECTOR('english',COALESCE(\"body\", '')),'B')) STORED",
        )
