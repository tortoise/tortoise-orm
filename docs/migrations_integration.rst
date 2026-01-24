Migration Integration
=====================

This page documents how the migrations runtime integrates with the Tortoise
initialization lifecycle, and how to configure apps for migrations.

Initialization flow
-------------------

For migration operations that only need model state (for example
``makemigrations``), Tortoise can initialize apps without eagerly creating
connection clients::

    await Tortoise.init(
        config=...,  # or config_file=...
        init_connections=False,
    )

When ``init_connections`` is ``False``, Tortoise still validates that each
app's ``default_connection`` exists in the config. Connection clients are
created lazily when a migration executor requests them.

Migration configuration
-----------------------

Configure each app with a ``migrations`` module path alongside ``models``
and ``default_connection``::

    await Tortoise.init(
        config={
            "connections": {
                "default": "sqlite://db.sqlite3",
            },
            "apps": {
                "users": {
                    "models": ["myapp.models"],
                    "default_connection": "default",
                    "migrations": "myapp.migrations",
                },
            },
        },
        init_connections=False,
    )

Runtime entry points
--------------------

The migration API and CLI are thin wrappers around this initialization:

- ``tortoise.migrations.api.migrate`` initializes apps with
  ``init_connections=False`` and then runs the executor per connection.
- ``tortoise.migrations.api.plan`` uses the same flow to build a plan without
  executing SQL.
- ``tortoise.cli makemigrations`` also uses ``init_connections=False`` to
  avoid creating connection clients when only state is required.
