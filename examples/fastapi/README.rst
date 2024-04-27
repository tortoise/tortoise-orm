Tortoise-ORM FastAPI example
============================

We have a lightweight integration util ``tortoise.contrib.fastapi`` which has a class ``RegisterTortoise`` that can be used to set/clean up Tortoise-ORM in lifespan context.

Usage
-----

.. code-block:: sh

    uvicorn main:app --reload
