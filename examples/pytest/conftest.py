"""
Pytest configuration with Tortoise ORM fixtures.

This example demonstrates how to set up Tortoise ORM for testing with pytest-asyncio.
Works with any database backend (SQLite, PostgreSQL, MySQL, etc.)
"""

import os

import pytest_asyncio

from tortoise import Tortoise
from tortoise.contrib.test import create_db


def get_db_url() -> str:
    """Get database URL from environment or use default."""
    return os.environ.get("TORTOISE_TEST_DB", "sqlite://:memory:")


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def _init_db():
    """
    Initialize Tortoise ORM once per test session.

    Using scope="session" with loop_scope="session" ensures:
    1. Database is initialized only once
    2. All tests share the same event loop
    3. Connection pools work correctly with any backend
    """
    await create_db(
        modules=["examples.pytest.models"],
        db_url=get_db_url(),
        app_label="models",
    )
    yield
    await Tortoise._drop_databases()


@pytest_asyncio.fixture(loop_scope="session")
async def db(_init_db):
    """
    Database fixture that ensures clean state for each test.

    Depends on _init_db which sets up the database once per session.
    This fixture clears data before each test for isolation.
    """
    # Clean up any existing data from previous tests
    for model in Tortoise.apps.get_models_iterable():
        await model.all().delete()
    yield


@pytest_asyncio.fixture(loop_scope="session")
async def db_with_user(db):
    """
    Database fixture with a pre-created user.

    This fixture depends on the `db` fixture and adds test data.
    Useful when multiple tests need the same initial data.
    """
    from examples.pytest.models import User

    user = await User.create(
        username="testuser",
        email="test@example.com",
    )
    yield user
    # No need to clean up - the `db` fixture handles database teardown


@pytest_asyncio.fixture(loop_scope="session")
async def db_with_posts(db):
    """
    Database fixture with a user and multiple posts.

    Demonstrates pre-populating the database with related data.
    """
    from examples.pytest.models import Post, User

    user = await User.create(
        username="author",
        email="author@example.com",
    )

    posts = []
    for i in range(3):
        post = await Post.create(
            title=f"Post {i + 1}",
            content=f"Content for post {i + 1}",
            author=user,
        )
        posts.append(post)

    yield {"user": user, "posts": posts}
