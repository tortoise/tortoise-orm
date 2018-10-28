======
Set up
======

.. _init_app:

Init app
========

After you defined all your models, tortoise needs you to init them, in order to create backward relations between models and match your db client with appropriate models.

You can do it like this:

.. code-block:: python3

    from tortoise import Tortoise
    from tortoise.utils import generate_schema

    async def init():
        # Here we create a SQLite DB using file "db.sqlite3"
        #  also specify the app name of "models"
        #  which contain models from "app.models"
        await Tortoise.init(
            db_url='sqlite://db.sqlite3',
            modules={'models': ['app.models']}
        )
        # Generate the schema
        await Tortoise.generate_schemas()
    
    
Here we create connection to SQLite database client and then we discover & initialise models.

``generate_schema`` generates schema on empty database, you shouldn't run it on every app init, run it just once, maybe out of your main code.

.. _cleaningup:

The Importance of cleaning up
=============================

Tortoise ORM will keep connections open to external Databases. As an ``asyncio`` Python library, it needs to have the connections closed properly or the Python interpreter may still wait for the completion of said connections.

To ensure connections are closed please ensure that ``Tortoise.close_connections()`` is called:

.. code-block:: python3

    await Tortoise.close_connections()

The small helper function ``tortoise.run_async()`` will ensure that connections are closed.

Reference
=========

.. autoclass:: tortoise.Tortoise
    :members:
    :undoc-members:

.. autofunction:: tortoise.run_async

