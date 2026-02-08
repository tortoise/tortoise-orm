import pytest_asyncio

from tortoise.contrib.test import tortoise_test_context


@pytest_asyncio.fixture(scope="function")
async def db():
    """Function-scoped fixture for isolated tests."""
    async with tortoise_test_context(["examples.pytest.models"]) as ctx:
        yield ctx
