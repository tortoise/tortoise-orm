.. _connections:

===========
Connections
===========

This document describes how to access database connections in Tortoise ORM.

.. contents::
    :local:
    :depth: 2

Accessing Connections
=====================

Tortoise ORM provides multiple ways to access database connections:

Via ``Tortoise`` Class (Recommended)
------------------------------------

The simplest way to access connections:

.. code-block:: python

    from tortoise import Tortoise

    # Get a specific connection by alias
    conn = Tortoise.get_connection("default")

    # Execute raw queries
    result = await conn.execute_query('SELECT * FROM "user"')

Via Helper Functions
--------------------

For more direct access to the connection handler:

.. code-block:: python

    from tortoise.connection import get_connection, get_connections

    # Get a specific connection
    conn = get_connection("default")

    # Get the connection handler (access to all connections)
    handler = get_connections()
    all_connections = handler.all()

Via Context (Advanced)
----------------------

When working with explicit contexts:

.. code-block:: python

    from tortoise.context import TortoiseContext

    async with TortoiseContext() as ctx:
        await ctx.init(db_url="sqlite://:memory:", modules={"models": ["myapp.models"]})

        # Access connections via context
        conn = ctx.connections.get("default")

Connection Configuration
========================

Connections are configured when calling ``Tortoise.init()``:

.. code-block:: python

    await Tortoise.init(
        config={
            "connections": {
                "default": {
                    "engine": "tortoise.backends.sqlite",
                    "credentials": {"file_path": "example.sqlite3"},
                }
            },
            "apps": {
                "models": {"models": ["__main__"], "default_connection": "default"}
            },
        }
    )

Or using a DB URL:

.. code-block:: python

    await Tortoise.init(
        db_url="sqlite://example.sqlite3",
        modules={"models": ["__main__"]}
    )

Multiple Databases
==================

Configure multiple connections for different databases:

.. code-block:: python

    await Tortoise.init(
        config={
            "connections": {
                "default": "sqlite://primary.sqlite3",
                "secondary": "postgres://user:pass@localhost:5432/secondary",
            },
            "apps": {
                "primary_models": {
                    "models": ["myapp.primary_models"],
                    "default_connection": "default",
                },
                "secondary_models": {
                    "models": ["myapp.secondary_models"],
                    "default_connection": "secondary",
                }
            },
        }
    )

    # Access specific connections
    primary_conn = Tortoise.get_connection("default")
    secondary_conn = Tortoise.get_connection("secondary")

Please refer to :ref:`this example<example_two_databases>` for a detailed demonstration.

Closing Connections
===================

Always close connections when shutting down your application:

.. code-block:: python

    # Close all connections
    await Tortoise.close_connections()

    # Or via helper function
    from tortoise.connection import get_connections
    await get_connections().close_all()

In framework integrations, this is typically handled automatically on shutdown.

Connection Lifecycle
====================

Connections are created lazily when first accessed and are managed by the
``ConnectionHandler`` class. Each ``TortoiseContext`` has its own ``ConnectionHandler``,
providing isolation between different contexts (useful for testing).

.. code-block:: python

    # Connection is created on first access
    conn = Tortoise.get_connection("default")

    # Same connection is returned on subsequent calls
    conn2 = Tortoise.get_connection("default")
    assert conn is conn2

    # Closing discards the connection
    await Tortoise.close_connections()

    # Next access creates a new connection
    conn3 = Tortoise.get_connection("default")
    assert conn is not conn3

Event Loop Handling
===================

Some database drivers (asyncpg, aiomysql) bind their connection pools to the event loop
that created them. If the loop changes -- for example, when using function-scoped pytest
fixtures or Starlette's ``TestClient`` -- the old pool becomes unusable.

Tortoise handles this automatically: when ``ConnectionHandler.get()`` detects that the
current event loop differs from the one the connection was created on, it transparently
creates a fresh connection.

**In production**, a loop change usually indicates a bug (e.g., mixing sync/async code).
A ``TortoiseLoopSwitchWarning`` is emitted so you can investigate:

.. code-block:: python

    import warnings
    from tortoise.warnings import TortoiseLoopSwitchWarning

    # Suppress if you know what you're doing
    warnings.filterwarnings("ignore", category=TortoiseLoopSwitchWarning)

**In tests**, ``tortoise_test_context()`` suppresses this warning automatically.
No special configuration needed.

.. list-table:: Backend Loop Binding
   :header-rows: 1
   :widths: 30 20 50

   * - Backend
     - Bound?
     - Notes
   * - asyncpg
     - Yes
     - Pool stores loop at creation time
   * - aiomysql/asyncmy
     - Yes
     - Pool stores loop at creation time
   * - psycopg
     - No
     - Uses running loop per-operation
   * - aiosqlite
     - Partial
     - Grabs loop per-operation, not at creation
   * - asyncodbc (MSSQL/Oracle)
     - No
     - Per-operation loop resolution

API Reference
=============

.. _connection_handler:

Helper Functions
----------------

.. autofunction:: tortoise.connection.get_connection

.. autofunction:: tortoise.connection.get_connections

ConnectionHandler Class
-----------------------

.. autoclass:: tortoise.connection.ConnectionHandler
    :members:
    :undoc-members:

Migration from Legacy API
=========================

If you're upgrading from an older version that used the ``connections`` singleton,
see the :ref:`migration_guide` for details.

.. note::

    The ``connections`` singleton still works but is deprecated. It now acts as a
    proxy that delegates to the current context's ``ConnectionHandler``. New code
    should use ``get_connection()`` / ``get_connections()`` or ``Tortoise.get_connection()``.

**Quick reference:**

.. list-table:: API Migration
   :header-rows: 1
   :widths: 50 50

   * - Old Pattern (Deprecated)
     - New Pattern
   * - ``from tortoise import connections``
     - ``from tortoise.connection import get_connections``
   * - ``connections.get("alias")``
     - ``Tortoise.get_connection("alias")``
   * - ``connections.all()``
     - ``get_connections().all()``
   * - ``connections.close_all()``
     - ``Tortoise.close_connections()``
