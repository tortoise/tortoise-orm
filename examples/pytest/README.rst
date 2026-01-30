=======================
Pytest Example
=======================

This example demonstrates how to set up Tortoise ORM for testing with pytest
and pytest-asyncio using the ``create_db`` async function.

Structure
=========

- ``models.py`` - Example Tortoise ORM models (User and Post)
- ``conftest.py`` - Pytest fixtures using ``create_db``
- ``test_models.py`` - Example tests demonstrating various testing patterns

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

Key Concepts
============

Using ``create_db`` in fixtures
-------------------------------

The ``create_db`` function is an async helper that initializes Tortoise ORM
for testing. It's designed for use in pytest-asyncio fixtures:

.. code-block:: python

    import pytest_asyncio
    from tortoise import Tortoise
    from tortoise.contrib.test import create_db

    @pytest_asyncio.fixture
    async def db():
        await create_db(
            modules=["myapp.models"],
            db_url="sqlite://:memory:",
            app_label="models",
        )
        yield
        await Tortoise._drop_databases()

Database isolation
------------------

Each test gets a completely fresh database. The fixture:

1. Creates all tables before the test
2. Yields control to the test
3. Drops all tables after the test

This ensures tests don't interfere with each other.

Pre-populated fixtures
----------------------

You can create fixtures that pre-populate data:

.. code-block:: python

    @pytest_asyncio.fixture
    async def db_with_user(db):
        from myapp.models import User
        user = await User.create(username="testuser", email="test@example.com")
        yield user
        # Cleanup handled by db fixture

Fixture dependencies allow you to build complex test scenarios while keeping
the setup code DRY.
