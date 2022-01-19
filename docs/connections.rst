.. _connections:

===========
Connections
===========

This document describes how to access the underlying connection object (:ref:`BaseDBAsyncClient<base_db_client>`) for the aliases defined
as part of the DB config passed to the :meth:`Tortoise.init<tortoise.Tortoise.init>` call.

Below is a simple code snippet which shows how the interface can be accessed:

.. code-block::  python3

    # connections is a singleton instance of the ConnectionHandler class and serves as the
    # entrypoint to access all connection management APIs.
    from tortoise import connections


    # Assume that this is the Tortoise configuration used
    await Tortoise.init(
        {
            "connections": {
                "default": {
                    "engine": "tortoise.backends.sqlite",
                    "credentials": {"file_path": "example.sqlite3"},
                }
            },
            "apps": {
                "events": {"models": ["__main__"], "default_connection": "default"}
            },
        }
    )

    conn: BaseDBAsyncClient = connections.get("default")
    try:
        await conn.execute_query('SELECT * FROM "event"')
    except OperationalError:
        print("Expected it to fail")

.. important::
    The :ref:`tortoise.connection.ConnectionHandler<connection_handler>` class has been implemented with the singleton
    pattern in mind and so when the ORM initializes, a singleton instance of this class
    ``tortoise.connection.connections`` is created automatically and lives in memory up until the lifetime of the app.
    Any attempt to modify or override its behaviour at runtime is risky and not recommended.


Please refer to :ref:`this example<example_two_databases>` for a detailed demonstration of how this API can be used
in practice.


API Reference
===========

.. _connection_handler:

.. automodule:: tortoise.connection
    :members:
    :undoc-members: