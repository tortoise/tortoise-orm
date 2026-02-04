"""
Custom fixtures for PostgreSQL-specific tests that require specific model modules.

These fixtures support tests that define tortoise_test_modules to use
custom model definitions for PostgreSQL features like TSVector.
"""

import os

import pytest
import pytest_asyncio

from tortoise.context import tortoise_test_context


def skip_if_not_postgres():
    """Skip test if not running against PostgreSQL."""
    db_url = os.getenv("TORTOISE_TEST_DB", "")
    if db_url.split(":", 1)[0] not in {"postgres", "asyncpg", "psycopg"}:
        pytest.skip("Postgres-only test.")


@pytest_asyncio.fixture(scope="module")
async def db_module_postgres():
    """
    Module-scoped fixture for postgres tests using standard testmodels.

    Creates a TortoiseContext with tests.testmodels once per test module.
    Used as base for postgres tests that need standard models like TextFields.
    """
    skip_if_not_postgres()
    db_url = os.getenv("TORTOISE_TEST_DB", "sqlite://:memory:")
    async with tortoise_test_context(
        modules=["tests.testmodels"],
        db_url=db_url,
        app_label="models",
        connection_label="models",
    ) as ctx:
        yield ctx


@pytest_asyncio.fixture(scope="function")
async def db_postgres(db_module_postgres):
    """
    Function-scoped fixture with transaction rollback for postgres tests.

    Equivalent to: test.TestCase with standard testmodels.
    """
    conn = db_module_postgres.db()
    transaction = conn._in_transaction()
    await transaction.__aenter__()

    try:
        yield db_module_postgres
    finally:

        class _RollbackException(Exception):
            pass

        await transaction.__aexit__(_RollbackException, _RollbackException(), None)


@pytest_asyncio.fixture(scope="function")
async def db_tsvector():
    """
    Fixture for TestTSVectorField.

    Uses models defined in tests.contrib.postgres.models_tsvector module.
    Equivalent to: test.IsolatedTestCase with tortoise_test_modules
    """
    skip_if_not_postgres()
    db_url = os.getenv("TORTOISE_TEST_DB", "sqlite://:memory:")
    async with tortoise_test_context(
        modules=["tests.contrib.postgres.models_tsvector"],
        db_url=db_url,
        app_label="models",
        connection_label="models",
    ) as ctx:
        yield ctx


@pytest_asyncio.fixture(scope="function")
async def db_search():
    """
    Fixture for TestPostgresSearchLookupTSVector.

    Uses models defined in tests.contrib.postgres.models_tsvector module.
    Equivalent to: test.IsolatedTestCase with tortoise_test_modules
    """
    skip_if_not_postgres()
    db_url = os.getenv("TORTOISE_TEST_DB", "sqlite://:memory:")
    async with tortoise_test_context(
        modules=["tests.contrib.postgres.models_tsvector"],
        db_url=db_url,
        app_label="models",
        connection_label="models",
    ) as ctx:
        yield ctx
