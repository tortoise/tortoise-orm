.. _cli:

===========
Tortoise CLI
===========

This document describes the built-in Tortoise CLI, built on top of asyncclick and ptpython.

Installation
============

.. code-block:: shell

    pip install tortoise-orm[cli]

Quick Start
===========

.. code-block:: shell

    > tortoise -h
    Usage: tortoise [OPTIONS] COMMAND [ARGS]...

    Options:
      -V, --version        Show the version and exit.
      -c, --config TEXT    TortoiseORM config dictionary path, like settings.TORTOISE_ORM
      --config-file TEXT   Path to a JSON/YAML config file for TortoiseORM
      -h, --help           Show this message and exit.

    Commands:
      downgrade  Unapply migrations.
      heads      List migration heads on disk.
      history    List applied migrations from the database.
      init       Create migrations packages for configured apps.
      makemigrations  Create new migrations from model changes.
      migrate    Apply migrations.
      shell      Start an interactive shell.
      upgrade    Apply migrations (alias for migrate).

Usage
=====

Define a TortoiseORM config object, for example in ``settings.py``:

.. code-block:: python

    TORTOISE_ORM = {
        "connections": {
            "default": "sqlite://:memory:",
        },
        "apps": {
            "models": {
                "models": ["examples.models"],
                "default_connection": "default",
                "migrations": "examples.migrations",
            },
        },
    }

You can also set it in ``pyproject.toml``:

.. code-block:: toml

    [tool.tortoise]
    tortoise_orm = "settings.TORTOISE_ORM"

Interactive shell
=================

.. code-block:: shell

    tortoise -c settings.TORTOISE_ORM shell

Or set it in the environment and run:

.. code-block:: shell

    export TORTOISE_ORM=settings.TORTOISE_ORM
    tortoise shell

Migrations
==========

Initialize migrations package (creates ``migrations/__init__.py``):

.. code-block:: shell

    tortoise init

Create new migrations (autodetect changes):

.. code-block:: shell

    tortoise makemigrations

Apply migrations (latest for all apps):

.. code-block:: shell

    tortoise migrate

Apply migrations for a specific app:

.. code-block:: shell

    tortoise migrate models

Apply/rollback to a specific migration:

.. code-block:: shell

    tortoise migrate models 0002_add_field
    tortoise downgrade models 0001_initial

Inspect applied migrations and heads:

.. code-block:: shell

    tortoise history
    tortoise heads
