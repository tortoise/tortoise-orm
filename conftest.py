"""
Pytest configuration for Tortoise ORM tests.

Uses function-scoped fixtures for true test isolation.
"""

import os

import pytest
import pytest_asyncio

from tortoise.context import tortoise_test_context


@pytest.fixture(scope="session", autouse=True)
def configure_psycopg():
    """Configure psycopg timeout for faster tests."""
    try:
        from tortoise.backends.psycopg import PsycopgClient

        PsycopgClient.default_timeout = float(os.environ.get("TORTOISE_POSTGRES_TIMEOUT", "15"))
    except ImportError:
        pass


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def _truncate_all_tables(ctx) -> None:
    """Truncate all tables in the given context."""
    if ctx.apps:
        for model in ctx.apps.get_models_iterable():
            quote_char = model._meta.db.query_class.SQL_CONTEXT.quote_char
            await model._meta.db.execute_script(
                f"DELETE FROM {quote_char}{model._meta.db_table}{quote_char}"  # nosec
            )


# ============================================================================
# PYTEST FIXTURES FOR TESTS
# These fixtures provide different isolation patterns for test scenarios
# ============================================================================


@pytest_asyncio.fixture(scope="module")
async def db_module():
    """
    Module-scoped fixture: Creates TortoiseContext once per test module.

    This is the base fixture that creates the database schema once per module.
    Other fixtures build on top of this for different isolation strategies.

    Note: Uses connection_label="models" to match standard test infrastructure.
    """
    db_url = os.getenv("TORTOISE_TEST_DB", "sqlite://:memory:")
    async with tortoise_test_context(
        modules=["tests.testmodels"],
        db_url=db_url,
        app_label="models",
        connection_label="models",
    ) as ctx:
        yield ctx


@pytest_asyncio.fixture(scope="function")
async def db(db_module):
    """
    Function-scoped fixture with transaction rollback cleanup.

    Each test runs inside a transaction that gets rolled back at the end,
    providing isolation without the overhead of schema recreation.

    For databases that don't support transactions (e.g., MySQL MyISAM),
    falls back to truncation cleanup.

    This is the FASTEST isolation method - use for most tests.

    Usage:
        @pytest.mark.asyncio
        async def test_something(db):
            obj = await Model.create(name="test")
            assert obj.id is not None
            # Changes are rolled back after test
    """
    # Get connection from the context using its default connection
    conn = db_module.db()

    # Check if the database supports transactions
    if conn.capabilities.supports_transactions:
        # Start a savepoint/transaction
        transaction = conn._in_transaction()
        await transaction.__aenter__()

        try:
            yield db_module
        finally:
            # Rollback the transaction (discards all changes made during test)
            class _RollbackException(Exception):
                pass

            await transaction.__aexit__(_RollbackException, _RollbackException(), None)
    else:
        # For databases without transaction support (e.g., MyISAM),
        # fall back to truncation cleanup
        yield db_module
        await _truncate_all_tables(db_module)


@pytest_asyncio.fixture(scope="function")
async def db_simple(db_module):
    """
    Function-scoped fixture with NO cleanup between tests.

    Tests share state - data from one test persists to the next within the module.
    Use ONLY for read-only tests or tests that manage their own cleanup.

    Usage:
        @pytest.mark.asyncio
        async def test_read_only(db_simple):
            # Read-only operations, no writes
            config = get_config()
            assert "host" in config
    """
    yield db_module


@pytest_asyncio.fixture(scope="function")
async def db_isolated():
    """
    Function-scoped fixture with full database recreation per test.

    Creates a completely fresh database for EACH test. This is the SLOWEST
    method but provides maximum isolation.

    Use when:
    - Testing database creation/dropping
    - Tests need custom model modules
    - Tests must have completely clean state

    Usage:
        @pytest.mark.asyncio
        async def test_with_fresh_db(db_isolated):
            # Completely fresh database
            ...
    """
    db_url = os.getenv("TORTOISE_TEST_DB", "sqlite://:memory:")
    async with tortoise_test_context(
        modules=["tests.testmodels"],
        db_url=db_url,
        app_label="models",
        connection_label="models",
    ) as ctx:
        yield ctx


@pytest_asyncio.fixture(scope="function")
async def db_truncate(db_module):
    """
    Function-scoped fixture with table truncation cleanup.

    After each test, all tables are truncated (DELETE FROM).
    Faster than db_isolated but slower than db (transaction rollback).

    Use when testing transaction behavior (can't use rollback for cleanup).

    Usage:
        @pytest.mark.asyncio
        async def test_with_transactions(db_truncate):
            async with in_transaction():
                await Model.create(name="test")
            # Table truncated after test
    """
    yield db_module
    await _truncate_all_tables(db_module)


# ============================================================================
# HELPER FIXTURES
# ============================================================================


def make_db_fixture(
    modules: list[str], app_label: str = "models", connection_label: str = "models"
):
    """
    Factory function to create custom db fixtures with different modules.

    Use this in subdirectory conftest.py files for tests that need
    custom model modules.

    Example usage in tests/fields/conftest.py:
        db_array = make_db_fixture(["tests.fields.test_array"])

    Args:
        modules: List of module paths to discover models from.
        app_label: The app label for the models, defaults to "models".
        connection_label: The connection alias name, defaults to "models".

    Returns:
        An async fixture function.
    """

    @pytest_asyncio.fixture(scope="function")
    async def _db_fixture():
        db_url = os.getenv("TORTOISE_TEST_DB", "sqlite://:memory:")
        async with tortoise_test_context(
            modules=modules,
            db_url=db_url,
            app_label=app_label,
            connection_label=connection_label,
        ) as ctx:
            yield ctx

    return _db_fixture
