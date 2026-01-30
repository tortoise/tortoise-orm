=======================
Pytest Example
=======================

This example demonstrates how to set up Tortoise ORM for testing with pytest
and pytest-asyncio using the ``create_db`` async function.

**Works with all database backends**: SQLite, PostgreSQL, MySQL, etc.

Structure
=========

- ``models.py`` - Example Tortoise ORM models (User and Post)
- ``conftest.py`` - Pytest fixtures using ``create_db``
- ``test_models.py`` - Example tests demonstrating various testing patterns
- ``pyproject.toml`` - pytest-asyncio configuration for session-scoped event loops

Requirements
============

.. code-block:: bash

    pip install pytest pytest-asyncio tortoise-orm

Running Tests
=============

From the repository root:

.. code-block:: bash

    # Run with default in-memory SQLite
    pytest examples/pytest/test_models.py -v

    # Run with a specific database
    TORTOISE_TEST_DB="sqlite:///test.db" pytest examples/pytest/test_models.py -v

    # Run with PostgreSQL
    TORTOISE_TEST_DB="asyncpg://user:pass@localhost:5432/testdb" pytest examples/pytest/test_models.py -v

    # Run with MySQL
    TORTOISE_TEST_DB="mysql://user:pass@localhost:3306/testdb" pytest examples/pytest/test_models.py -v

Key Concepts
============

Session-scoped initialization with ``create_db``
------------------------------------------------

For connection-pooling databases (PostgreSQL, MySQL), all async operations
must use the same event loop. This is achieved by:

1. Using ``scope="session"`` and ``loop_scope="session"`` for the init fixture
2. Configuring pytest-asyncio to use session-scoped event loops

.. code-block:: python

    # pyproject.toml
    [tool.pytest.ini_options]
    asyncio_mode = "auto"
    asyncio_default_fixture_loop_scope = "session"
    asyncio_default_test_loop_scope = "session"

.. code-block:: python

    # conftest.py
    import pytest_asyncio
    from tortoise import Tortoise
    from tortoise.contrib.test import create_db

    @pytest_asyncio.fixture(scope="session", loop_scope="session")
    async def _init_db():
        await create_db(
            modules=["myapp.models"],
            db_url=get_db_url(),
            app_label="models",
        )
        yield
        await Tortoise._drop_databases()

    @pytest_asyncio.fixture(loop_scope="session")
    async def db(_init_db):
        # Clean up data between tests for isolation
        for model in Tortoise.apps.get_models_iterable():
            await model.all().delete()
        yield

Database isolation
------------------

The database is initialized once per session. Each test gets isolation through
data cleanup - all tables are cleared before each test runs.

Pre-populated fixtures
----------------------

You can create fixtures that pre-populate data:

.. code-block:: python

    @pytest_asyncio.fixture(loop_scope="session")
    async def db_with_user(db):
        from myapp.models import User
        user = await User.create(username="testuser", email="test@example.com")
        yield user
        # Cleanup handled by db fixture

Fixture dependencies allow you to build complex test scenarios while keeping
the setup code DRY.
