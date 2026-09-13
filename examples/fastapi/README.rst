Tortoise-ORM FastAPI example
============================

We have a lightweight integration util ``tortoise.contrib.fastapi`` which has a class ``RegisterTortoise`` that can be used to set/clean up Tortoise-ORM in lifespan context.

Setup
-----

Initialize the migrations directory (one-time, already done in this example):

.. code-block:: sh

    python -m tortoise -c config.TORTOISE_ORM init

Create migrations when models change:

.. code-block:: sh

    python -m tortoise -c config.TORTOISE_ORM makemigrations

Apply migrations to the database:

.. code-block:: sh

    python -m tortoise -c config.TORTOISE_ORM migrate

Run
---

.. code-block:: sh

    uvicorn main:app --reload
