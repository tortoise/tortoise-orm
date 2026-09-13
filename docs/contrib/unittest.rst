.. _unittest:

==============
Testing Support
==============

Tortoise ORM provides testing utilities designed for pytest with true test isolation.
Each test gets its own database context, ensuring tests don't interfere with each other.

.. contents::
    :local:
    :depth: 2

Quick Start
===========

1. Create a ``conftest.py`` file in your tests directory:

.. code-block:: python

    import os
    import pytest_asyncio
    from tortoise.contrib.test import tortoise_test_context

    @pytest_asyncio.fixture
    async def db():
        """Provide isolated database context for each test."""
        db_url = os.getenv("TORTOISE_TEST_DB", "sqlite://:memory:")
        async with tortoise_test_context(["myapp.models"], db_url=db_url) as ctx:
            yield ctx

2. Write your tests as async functions:

.. code-block:: python

    import pytest
    from myapp.models import User

    @pytest.mark.asyncio
    async def test_create_user(db):
        user = await User.create(name="Test User", email="test@example.com")
        assert user.id is not None
        assert user.name == "Test User"

    @pytest.mark.asyncio
    async def test_filter_users(db):
        await User.create(name="Alice")
        await User.create(name="Bob")

        users = await User.filter(name="Alice")
        assert len(users) == 1
        assert users[0].name == "Alice"

3. Run your tests:

.. code-block:: bash

    pytest tests/ -v

``tortoise_test_context`` Reference
===================================

The ``tortoise_test_context`` function creates an isolated ORM context for testing:

.. code-block:: python

    from tortoise.contrib.test import tortoise_test_context

    async with tortoise_test_context(
        modules=["myapp.models"],           # Required: List of model modules
        db_url="sqlite://:memory:",         # Optional: Database URL (default: sqlite://:memory:)
        app_label="models",                 # Optional: App label (default: "models")
        connection_label="default",         # Optional: Connection alias (default: "default")
    ) as ctx:
        # Your test code here
        pass

**Parameters:**

- ``modules`` (list): List of module paths containing your models. Required.
- ``db_url`` (str): Database connection URL. Defaults to ``sqlite://:memory:``.
- ``app_label`` (str): Label for the app in the ORM registry. Defaults to ``"models"``.
- ``connection_label`` (str): Alias for the database connection. Defaults to ``"default"``.

The context manager:

1. Creates a fresh ``TortoiseContext``
2. Initializes the ORM with the given configuration
3. Generates database schemas
4. Yields the context for your test
5. Closes all connections on exit

Testing with Multiple Databases
===============================

For tests that require multiple database connections:

.. code-block:: python

    import pytest_asyncio
    from tortoise.context import TortoiseContext

    @pytest_asyncio.fixture
    async def multi_db():
        """Fixture for testing with multiple databases."""
        async with TortoiseContext() as ctx:
            await ctx.init(config={
                "connections": {
                    "primary": "sqlite://:memory:",
                    "secondary": "sqlite://:memory:",
                },
                "apps": {
                    "models": {
                        "models": ["myapp.models"],
                        "default_connection": "primary",
                    },
                    "archive": {
                        "models": ["myapp.archive_models"],
                        "default_connection": "secondary",
                    }
                }
            })
            await ctx.generate_schemas()
            yield ctx

Event Loop Isolation
====================

Some backends (asyncpg, aiomysql) bind connection pools to the event loop that created
them. ``tortoise_test_context()`` handles this transparently -- if the event loop changes
between tests, connections are automatically recreated.

This means you **don't** need ``loop_scope="session"`` or any special pytest-asyncio
configuration. The simplest setup works:

.. code-block:: toml

    # pyproject.toml -- no loop_scope overrides needed
    [tool.pytest.ini_options]
    asyncio_mode = "auto"

If you use ``TortoiseContext`` directly (without ``tortoise_test_context``), you may see
a ``TortoiseLoopSwitchWarning`` when the loop changes. Suppress it with:

.. code-block:: python

    import warnings
    from tortoise.warnings import TortoiseLoopSwitchWarning
    warnings.filterwarnings("ignore", category=TortoiseLoopSwitchWarning)

Unit Testing Without a Database
================================

For testing pure business logic that reads model attributes and iterates relations
without making queries, use ``Model.construct()`` to create model instances in memory:

.. code-block:: python

    from myapp.models import User, Organization, Membership

    def test_user_has_active_membership():
        org = Organization.construct(id=1, name="Corp")
        membership = Membership.construct(
            organization=org,
            role="admin",
            is_active=True,
        )
        user = User.construct(
            id=1,
            email="test@example.com",
            memberships=[membership],
        )

        # Pure business logic -- no database needed
        active = [m for m in user.memberships if m.is_active]
        assert len(active) == 1
        assert active[0].role == "admin"

``construct()`` creates "detached" instances that behave like ORM-loaded objects:

- Reverse FK fields (e.g., ``user.memberships``) accept lists and wrap them in
  ``ReverseRelation``, so ``len()``, ``in``, iteration, and ``bool()`` all work.
- M2M fields work the same way, wrapped in ``ManyToManyRelation``.
- FK fields populate the source field automatically
  (e.g., ``event.tournament_id`` is set from ``tournament.pk``).
- No validation is performed -- null checks, type checks, and ``_saved_in_db``
  guards are all skipped.

.. note::

    ``construct()`` requires Tortoise to be initialized (via ``tortoise_test_context``
    or ``Tortoise.init()``) for relation fields to work, because relation metadata is
    resolved during initialization. For simple data-only fields, it works without
    initialization.

See :meth:`tortoise.models.Model.construct` for the full API reference.

Testing Database Capabilities
=============================

Use ``requireCapability`` to skip tests based on database capabilities:

.. code-block:: python

    from tortoise.contrib.test import requireCapability

    @pytest.mark.asyncio
    @requireCapability(dialect="postgres")
    async def test_postgres_specific_feature(db):
        """This test only runs on PostgreSQL."""
        # Test postgres-specific functionality
        pass

    @pytest.mark.asyncio
    @requireCapability(dialect="sqlite")
    async def test_sqlite_specific_feature(db):
        """This test only runs on SQLite."""
        pass

Environment Variables
=====================

Configure your test database via environment variables:

.. code-block:: bash

    # SQLite (default)
    export TORTOISE_TEST_DB="sqlite://:memory:"

    # PostgreSQL
    export TORTOISE_TEST_DB="postgres://user:pass@localhost:5432/testdb"

    # MySQL
    export TORTOISE_TEST_DB="mysql://user:pass@localhost:3306/testdb"

Using ``{}`` in the URL creates randomized database names (useful for parallel testing):

.. code-block:: bash

    export TORTOISE_TEST_DB="sqlite:///tmp/test-{}.sqlite"
    export TORTOISE_TEST_DB="postgres://user:pass@localhost:5432/test_{}"

Utility Functions
=================

truncate_all_models
-------------------

Truncate all model tables in the current context. The function handles foreign key
constraints automatically:

- **PostgreSQL**: Uses a single ``TRUNCATE ... CASCADE`` statement (fast, single round-trip).
- **Other databases**: Deletes in topological order — child tables are emptied before the
  parent tables they reference, avoiding FK constraint violations.

.. code-block:: python

    from tortoise.contrib.test import truncate_all_models

    @pytest.mark.asyncio
    async def test_with_truncation(db):
        # Create some data
        await User.create(name="Test")

        # Truncate all tables (FK-safe)
        await truncate_all_models()

        # Tables are now empty
        count = await User.all().count()
        assert count == 0

Migration from Legacy Test Classes
==================================

If you're upgrading from the legacy ``test.TestCase`` classes, see the
:ref:`migration_guide` for detailed migration instructions.

**Quick reference:**

.. list-table:: Migration Mapping
   :header-rows: 1
   :widths: 40 60

   * - Legacy (Removed)
     - Modern Replacement
   * - ``test.TestCase``
     - pytest + ``db`` fixture
   * - ``test.IsolatedTestCase``
     - pytest + ``db`` fixture (isolation is default)
   * - ``test.TruncationTestCase``
     - pytest + ``db`` fixture + ``truncate_all_models()``
   * - ``test.SimpleTestCase``
     - pytest + ``db`` fixture
   * - ``initializer()``
     - ``tortoise_test_context()``
   * - ``finalizer()``
     - (automatic with context manager)
   * - ``self.assertEqual(a, b)``
     - ``assert a == b``
   * - ``self.assertIn(a, b)``
     - ``assert a in b``
   * - ``self.assertRaises(Exc)``
     - ``pytest.raises(Exc)``

Reference
=========

.. automodule:: tortoise.contrib.test
    :members: tortoise_test_context, truncate_all_models, requireCapability
    :show-inheritance:
