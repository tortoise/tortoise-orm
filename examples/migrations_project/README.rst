Migration Example Project
=========================

This example shows a minimal project with migrations enabled.

Setup
-----

From the repo root, create the migrations package and generate migrations:

.. code-block:: shell

    python3 -m tortoise.cli.cli -c examples.migrations_project.settings.TORTOISE_ORM init
    python3 -m tortoise.cli.cli -c examples.migrations_project.settings.TORTOISE_ORM makemigrations

Apply migrations:

.. code-block:: shell

    python3 -m tortoise.cli.cli -c examples.migrations_project.settings.TORTOISE_ORM migrate

Inspect migrations:

.. code-block:: shell

    python3 -m tortoise.cli.cli -c examples.migrations_project.settings.TORTOISE_ORM history
    python3 -m tortoise.cli.cli -c examples.migrations_project.settings.TORTOISE_ORM heads
