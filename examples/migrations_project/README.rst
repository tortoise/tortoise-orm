Migration Example Project
=========================

This example shows a minimal project with migrations enabled.

Setup
-----

From the repo root, create the migrations package and generate migrations:

.. code-block:: shell

    tortoise -c examples.migrations_project.settings.TORTOISE_ORM init
    tortoise -c examples.migrations_project.settings.TORTOISE_ORM makemigrations

Apply migrations:

.. code-block:: shell

    tortoise -c examples.migrations_project.settings.TORTOISE_ORM migrate

Inspect migrations:

.. code-block:: shell

    tortoise -c examples.migrations_project.settings.TORTOISE_ORM history
    tortoise -c examples.migrations_project.settings.TORTOISE_ORM heads

You can also invoke the CLI via Python if needed:

.. code-block:: shell

    python3 -m tortoise -c examples.migrations_project.settings.TORTOISE_ORM migrate
