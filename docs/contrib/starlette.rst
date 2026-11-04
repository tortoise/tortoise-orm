.. _contrib_starlette:

==================================
Tortoise-ORM Starlette integration
==================================

We have a lightweight integration util ``tortoise.contrib.starlette``, which includes a synchronous function `register_tortoise` that sets up Tortoise-ORM on startup and cleans it up on teardown, along with a class `RegisterTortoise` that can be used to set up and clean up Tortoise-ORM within a lifespan context.

See the :ref:`example_starlette`

Reference
=========

.. automodule:: tortoise.contrib.starlette
    :members:
    :undoc-members:
    :show-inheritance:
