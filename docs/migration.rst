.. _migration:

==========
Migrations
==========

This document describes the built-in Tortoise migration system and CLI.
It's designed to be clear and Tortoise native, while still being familiar.

.. note::
    Aerich is a legacy alternative. The built-in migrations described here are
    the recommended path going forward.

Quick start
===========

1) Configure migrations per app

.. code-block:: python

    TORTOISE_ORM = {
        "connections": {
            "default": "sqlite://db.sqlite3",
        },
        "apps": {
            "models": {
                "models": ["myapp.models"],
                "default_connection": "default",
                "migrations": "myapp.migrations",
            },
        },
    }

2) Initialize the migrations package

.. code-block:: shell

    tortoise init

3) Create and apply migrations

.. code-block:: shell

    tortoise makemigrations
    tortoise migrate

You can browse a working example in ``examples/migrations_project``.

CLI reference
=============

All commands share config resolution (``-c/--config``, ``--config-file``, or
``[tool.tortoise]`` in ``pyproject.toml``). The CLI favors explicit, copy/paste
friendly output.

init
----

Create migrations packages for configured apps.

.. code-block:: shell

    tortoise init

makemigrations
--------------

Autodetect model changes and create new migration files.

.. code-block:: shell

    tortoise makemigrations
    tortoise makemigrations --name add_posts_table
    tortoise makemigrations --empty

migrate / upgrade
-----------------

Apply migrations. ``upgrade`` is an alias of ``migrate``.

.. code-block:: shell

    tortoise migrate
    tortoise migrate models
    tortoise migrate models 0002_add_field

downgrade
---------

Unapply migrations for a specific app.

.. code-block:: shell

    tortoise downgrade models
    tortoise downgrade models 0001_initial

history
-------

List applied migrations from the database.

.. code-block:: shell

    tortoise history

heads
-----

List migration heads on disk.

.. code-block:: shell

    tortoise heads

Migration files
===============

Migration files are plain Python modules. Each module exposes a ``Migration``
class with attributes like ``dependencies`` and ``operations``. Operations are
serialized using ``deconstruct()`` so they can be re-imported and replayed.

Minimal example:

.. code-block:: python

    from tortoise import fields
    from tortoise.migrations import CreateModel
    from tortoise.migrations.migration import Migration

    class Migration(Migration):
        dependencies = []
        operations = [
            CreateModel(
                name="Post",
                fields={
                    "id": fields.IntField(pk=True),
                    "title": fields.CharField(max_length=200),
                },
                options={},
            ),
        ]

Historical models and data migrations
=====================================

Data migrations transform existing data during schema evolution. Tortoise
provides two operations for data migrations: ``RunPython`` for complex logic
and ``RunSQL`` for raw SQL execution.

RunPython
---------

Data migrations can use historical models via ``RunPython``. The migration
state recreates models as they existed at that point, so queries align with the
schema being migrated.

.. code-block:: python

    from tortoise.migrations import RunPython
    from tortoise.migrations.migration import Migration

    async def forwards(apps, schema_editor):
        Post = apps.get_model("models", "Post")
        await Post.all().update(title="Migrated")

    async def backwards(apps, schema_editor):
        Post = apps.get_model("models", "Post")
        await Post.all().update(title="Original")

    class Migration(Migration):
        dependencies = [("models", "0001_initial")]
        operations = [
            RunPython(code=forwards, reverse_code=backwards)
        ]

RunSQL
------

For simple data transformations, ``RunSQL`` executes raw SQL statements
directly. This is more efficient for bulk operations but database-specific.

.. code-block:: python

    from tortoise.migrations import RunSQL
    from tortoise.migrations.migration import Migration

    class Migration(Migration):
        dependencies = [("models", "0001_initial")]
        operations = [
            RunSQL(
                sql="UPDATE post SET title = 'Migrated' WHERE title IS NULL",
                reverse_sql="UPDATE post SET title = NULL WHERE title = 'Migrated'",
            ),
        ]

``RunSQL`` also supports parameterized queries and multiple statements:

.. code-block:: python

    RunSQL(
        sql=[
            ("INSERT INTO post (title) VALUES (?)", ["First"]),
            ("INSERT INTO post (title) VALUES (?)", ["Second"]),
        ],
        reverse_sql="DELETE FROM post WHERE title IN ('First', 'Second')",
    )

Choosing between RunPython and RunSQL
--------------------------------------

Use ``RunPython`` when:

- Logic requires conditionals or complex calculations
- Operations span multiple models or tables
- Database portability matters
- You need type safety and ORM features

Use ``RunSQL`` when:

- Simple UPDATE/INSERT/DELETE statements suffice
- Performance is critical for large datasets
- Database-specific features are needed
- Direct SQL is clearer than equivalent ORM code

Example combining both:

.. code-block:: python

    from tortoise.migrations import RunPython, RunSQL
    from decimal import Decimal

    async def calculate_totals(apps, schema_editor):
        Order = apps.get_model("shop", "Order")
        async for order in Order.all():
            # Complex calculation in Python
            order.total = Decimal(order.subtotal) * Decimal("1.08")
            await order.save()

    class Migration(Migration):
        dependencies = [("shop", "0005_add_total_field")]
        operations = [
            # Complex logic: use RunPython
            RunPython(code=calculate_totals, reverse_code=None),
            # Simple concatenation: use RunSQL
            RunSQL(
                sql="UPDATE customer SET full_name = first_name || ' ' || last_name",
                reverse_sql="UPDATE customer SET full_name = NULL",
            ),
        ]

Atomic control
--------------

``RunPython`` and ``RunSQL`` support an ``atomic`` parameter (default ``True``) to control transaction wrapping.
Set ``atomic=False`` for SQLite ``RunSQL`` operations to prevent connection deadlocks, or for PostgreSQL
``CREATE INDEX CONCURRENTLY`` which cannot run inside transactions.

FAQ / common errors
===================

Migrations are not found
    Check that each app config includes a ``migrations`` module path and that
    the package exists (``tortoise init`` creates it).

``App <label> has no migrations configured``
    Add ``"migrations": "myapp.migrations"`` to the app config and rerun.

``No module named <app>.migrations``
    Ensure the migrations package exists and is importable on ``PYTHONPATH``.

CLI shows no changes
    Make sure the models are imported by the configured app and that you
    initialized with the same config source (``-c`` or ``--config-file``).

Data migration fails to import models
    Use the historical models passed into ``RunPython`` via ``apps.get_model``
    rather than importing runtime model classes directly.

Making migrations irreversible
    Set ``reverse_code=None`` for ``RunPython`` or omit ``reverse_sql`` for
    ``RunSQL`` when the operation cannot be undone (e.g., destructive data
    changes). The migration will raise an error if you attempt to downgrade.

Migration package overview
==========================

The migration system is grouped into a few public entry points and internal
building blocks. Most users will only need the CLI, but these modules are
available when you need programmatic control or advanced workflows.

Public entry points
-------------------

- ``tortoise.migrations.api.migrate``: apply migrations programmatically.
- ``tortoise.migrations.api.plan``: build a dry-run plan without executing SQL.
- ``tortoise.migrations``: re-exports operations and helpers for authoring
  migrations (for example ``RunPython``, ``RunSQL``, or ``CreateModel``).

Runtime modules
---------------

- ``tortoise.migrations.executor``: migration planning and execution engine.
- ``tortoise.migrations.loader``: loads migration modules from disk.
- ``tortoise.migrations.graph``: dependency graph used for planning.
- ``tortoise.migrations.recorder``: stores and reads applied migrations.
- ``tortoise.migrations.migration``: ``Migration`` base class and apply/unapply
  flow.

Schema and state
----------------

- ``tortoise.migrations.schema_generator.state``: in-memory historical state.
- ``tortoise.migrations.schema_generator.state_apps``: app registry for
  historical models.
- ``tortoise.migrations.schema_editor``: backend schema editors for DDL.
- ``tortoise.migrations.operations``: operation definitions for schema changes.

Autodetection and writing
-------------------------

- ``tortoise.migrations.autodetector``: compares current apps to migration
  state and generates new operations.
- ``tortoise.migrations.writer``: renders operations to migration modules.
