.. _migration:

=========
Migration
=========

This document describes how to use `Aerich` to make migrations.

You can see `https://github.com/tortoise/aerich <https://github.com/tortoise/aerich>`_ for more details.

Quick Start
===========

.. code-block:: shell

    > aerich -h

    Usage: aerich [OPTIONS] COMMAND [ARGS]...

    Options:
      -c, --config TEXT  Config file.  [default: aerich.ini]
      --app TEXT         Tortoise-ORM app name.  [default: models]
      -n, --name TEXT    Name of section in .ini file to use for aerich config.
                         [default: aerich]
      -h, --help         Show this message and exit.

    Commands:
      downgrade  Downgrade to specified version.
      heads      Show current available heads in migrate location.
      history    List all migrate items.
      init       Init config file and generate root migrate location.
      init-db    Generate schema and generate app migrate location.
      migrate    Generate migrate changes file.
      upgrade    Upgrade to latest version.

Usage
=====

You need add `aerich.models` to your `Tortoise-ORM` config first,
example:

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

      Init config file and generate root migrate location.

    Options:
      -t, --tortoise-orm TEXT  Tortoise-ORM config module dict variable, like settings.TORTOISE_ORM.
                               [required]
      --location TEXT          Migrate store location.  [default: ./migrations]
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

