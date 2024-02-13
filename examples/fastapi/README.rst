Tortoise-ORM FastAPI example
============================

We have a lightweight integration util ``tortoise.contrib.fastapi`` which has a class ``RegisterTortoise`` that can be used to sets up and cleans up Tortoise-ORM in lifespan context.

Usage
-----

.. code-block:: sh

    uvicorn main:app --reload
