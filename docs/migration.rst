.. _migration:

=========
Migration
=========

.. note::
    Aerich is not as mature yet, expect some issues here and there.

This document describes how to use `Aerich` to manage schema changes.

Check out `aerich repository <https://github.com/tortoise/aerich>`_ for more details.

Quick Start
===========

.. code-block:: shell


    > aerich -h

    Usage: aerich [OPTIONS] COMMAND [ARGS]...

    Options:
      -V, --version      Show the version and exit.
      -c, --config TEXT  Config file.  [default: pyproject.toml]
      --app TEXT         Tortoise-ORM app name.
      -h, --help         Show this message and exit.

    Commands:
      downgrade  Downgrade to specified version.
      heads      Show currently available heads (unapplied migrations).
      history    List all migrations.
      init       Initialize aerich config and create migrations folder.
      init-db    Generate schema and generate app migration folder.
      inspectdb  Prints the current database tables to stdout as Tortoise-ORM...
      migrate    Generate a migration file for the current state of the models.
      upgrade    Upgrade to specified migration version.


Usage
=====

Add ``aerich.models`` to your `Tortoise-ORM` config first:

.. code-block:: python3

    TORTOISE_ORM = {
        "connections": {"default": "mysql://root:123456@127.0.0.1:3306/test"},
        "apps": {
            "models": {
                "models": ["tests.models", "aerich.models"],
                "default_connection": "default",
            },
        },
    }

Initialization
--------------

.. code-block:: shell

    > aerich init -h

    Usage: aerich init [OPTIONS]

      Initialize aerich config and create migrations folder.

    Options:
      -t, --tortoise-orm TEXT  Tortoise-ORM config dict location, like
                              `settings.TORTOISE_ORM`.  [required]
      --location TEXT          Migrations folder.  [default: ./migrations]
      -s, --src_folder TEXT    Folder of the source, relative to the project root.
      -h, --help               Show this message and exit.


Init config file and location:

.. code-block:: shell

    > aerich init -t tests.backends.mysql.TORTOISE_ORM

    Success create migrate location ./migrations
    Success generate config file aerich.ini


Init db
-------

.. code-block:: shell

    > aerich init-db

    Success create app migrate location ./migrations/models
    Success generate schema for app "models"


If your Tortoise-ORM app is not default `models`, you must specify
`--app` like `aerich --app other_models init-db`.

Update models and make migrate
------------------------------

..  code-block:: shell

    > aerich migrate --name drop_column

    Success migrate 1_202029051520102929_drop_column.json


Format of migrate filename is
`{version_num}_{datetime}_{name|update}.json`.

And if `aerich` guess you are renaming a column, it will ask `Rename {old_column} to {new_column} [True]`, you can choice `True` to rename column without column drop, or choice `False` to drop column then create.

If you use `MySQL`, only MySQL8.0+ support `rename..to` syntax.

Upgrade to latest version
-------------------------

.. code-block:: shell

    > aerich upgrade

    Success upgrade 1_202029051520102929_drop_column.json

Now your db is migrated to latest.

Downgrade to specified version
------------------------------

.. code-block:: shell

    > aerich init -h

    Usage: aerich downgrade [OPTIONS]

      Downgrade to specified version.

    Options:
      -v, --version INTEGER  Specified version, default to last.  [default: -1]
      -h, --help             Show this message and exit.

.. code-block:: shell

    > aerich downgrade

    Success downgrade 1_202029051520102929_drop_column.json


Now your db rollback to specified version.

Show history
------------

.. code-block:: shell

    > aerich history

    1_202029051520102929_drop_column.json


Show heads to be migrated
-------------------------

.. code-block:: shell

    > aerich heads

    1_202029051520102929_drop_column.json

