Tortoise-ORM BlackSheep example
============================

We have a lightweight integration util ``tortoise.contrib.blacksheep`` which has a single function ``register_tortoise`` which sets up Tortoise-ORM on startup and cleans up on teardown.

Usage
-----

.. code-block:: sh

    uvicorn server:app --reload
