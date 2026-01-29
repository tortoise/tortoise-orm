.. _cli:

===========
Tortoise CLI
===========

This page documents the built-in CLI for schema migrations and interactive use.

Overview
========

The CLI resolves configuration from ``-c/--config``, ``--config-file``, or
``[tool.tortoise]`` in ``pyproject.toml``. Migration commands mirror the
runtime API while adding plan/history output.

Basic usage
===========

.. code-block:: shell

    tortoise -h
    tortoise -c settings.TORTOISE_ORM init
    tortoise makemigrations
    tortoise migrate

Configuration resolution
========================

You can supply configuration in one of these ways:

- ``-c/--config`` with a dotted path to a config object
  (for example ``settings.TORTOISE_ORM``).
- ``--config-file`` with a JSON/YAML config file path.
- ``pyproject.toml`` with ``[tool.tortoise]`` and a ``tortoise_orm`` key.

Commands
========

init
----

Create migrations packages for configured apps. This ensures each app has a
``migrations`` module and the package is importable.

.. code-block:: shell

    tortoise init
    tortoise init users billing

makemigrations
--------------

Autodetect model changes and create new migration files.

.. code-block:: shell

    tortoise makemigrations
    tortoise makemigrations --name add_posts_table
    tortoise makemigrations users
    tortoise makemigrations --empty users

migrate / upgrade
-----------------

Apply migrations. ``migrate`` can move forward or backward depending on the
target. ``upgrade`` is forward-only and will refuse to roll back.

.. code-block:: shell

    tortoise migrate
    tortoise migrate users
    tortoise migrate users 0002_add_field
    tortoise migrate users.0002_add_field

downgrade
---------

Unapply migrations for a specific app. ``downgrade`` is backward-only and will
refuse to apply forward migrations. If no migration name is provided, it
targets the first migration for that app.

.. code-block:: shell

    tortoise downgrade users
    tortoise downgrade users 0001_initial

history
-------

List applied migrations from the database.

.. code-block:: shell

    tortoise history
    tortoise history users

heads
-----

List migration heads on disk.

.. code-block:: shell

    tortoise heads
    tortoise heads users

shell
-----

Start an interactive shell with Tortoise initialized.

.. code-block:: shell

    tortoise shell

Target shorthand
================

The migration commands accept Django-style targets:

- ``APP_LABEL`` means "latest" for that app.
- ``APP_LABEL MIGRATION`` targets a specific migration name.
- ``APP_LABEL.MIGRATION`` is equivalent to ``APP_LABEL MIGRATION`` and is
  convenient for copy/paste from history output.

.. code-block:: shell

    tortoise migrate users.__latest__
    tortoise migrate users 0003_add_index
    tortoise downgrade users.__first__
