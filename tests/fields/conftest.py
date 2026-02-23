"""
Custom fixtures for field tests that require specific model modules.

These fixtures support tests that define tortoise_test_modules to use
custom model definitions instead of the default tests.testmodels.
"""

import os

import pytest
import pytest_asyncio

from tortoise.context import tortoise_test_context


@pytest_asyncio.fixture(scope="function")
async def db_array_fields():
    """
    Fixture for TestArrayFields.

    Uses models defined in tests.testmodels_postgres module.
    Equivalent to: test.IsolatedTestCase with tortoise_test_modules=["tests.testmodels_postgres"]
    """
    db_url = os.getenv("TORTOISE_TEST_DB", "sqlite://:memory:")
    # Skip on non-Postgres databases since ArrayFields require Postgres
    if "postgres" not in db_url:
        pytest.skip("ArrayFields require PostgreSQL")
    async with tortoise_test_context(
        modules=["tests.testmodels_postgres"],
        db_url=db_url,
        app_label="models",
        connection_label="models",
    ) as ctx:
        yield ctx


@pytest_asyncio.fixture(scope="function")
async def db_subclass_fields():
    """
    Fixture for TestEnumField and TestCustomFieldFilters.

    Uses models defined in tests.fields.subclass_models module.
    Equivalent to: test.IsolatedTestCase with tortoise_test_modules=["tests.fields.subclass_models"]
    """
    db_url = os.getenv("TORTOISE_TEST_DB", "sqlite://:memory:")
    async with tortoise_test_context(
        modules=["tests.fields.subclass_models"],
        db_url=db_url,
        app_label="models",
        connection_label="models",
    ) as ctx:
        yield ctx
