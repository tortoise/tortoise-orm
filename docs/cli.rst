.. _cli:

===========
TortoiseCLI
===========

This document describes how to use `tortoise-cli`, a cli tool for tortoise-orm, build on top of click and ptpython.

You can see `https://github.com/tortoise/tortoise-cli <https://github.com/tortoise/tortoise-cli>`_ for more details.


Quick Start
===========

.. code-block:: shell

    > tortoise-cli -h                                                                                                                                                                 23:59:38
    Usage: tortoise-cli [OPTIONS] COMMAND [ARGS]...

    Options:
      -V, --version      Show the version and exit.
      -c, --config TEXT  TortoiseORM config dictionary path, like settings.TORTOISE_ORM
      -h, --help         Show this message and exit.

    Commands:
      shell  Start an interactive shell.

Usage
=====

First, you need make a TortoiseORM config object, assuming that in `settings.py`.

.. code-block:: shell

    TORTOISE_ORM = {
        "connections": {
            "default": "sqlite://:memory:",
        },
        "apps": {
            "models": {"models": ["examples.models"], "default_connection": "default"},
        },
    }


Interactive shell
=================

Then you can start an interactive shell for TortoiseORM.

.. code-block:: shell

    tortoise-cli -c settings.TORTOISE_ORM shell


Or you can set config by set environment variable.

.. code-block:: shell

    export TORTOISE_ORM=settings.TORTOISE_ORM

Then just run:

.. code-block:: shell

    tortoise-cli shell
