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
        # Here we connect to a PostgresQL DB
        #  also specify the app name of "models"
        #  which contain models from "app.models"
        await Tortoise.init(
            db_url='postgres://postgres:qwerty123@localhost:5432/events',
            modules={'models': ['app.models']}
        )
        # Generate the schema
        await Tortoise.generate_schemas()
    
    
Here we create connection to PostgresQL database with default ``asyncpg`` client and then we discover & initialise models.

``generate_schema`` generates schema on empty database, you shouldn't run it on every app init, run it just once, maybe out of your main code.

Reference
=========

.. autoclass:: tortoise.Tortoise
    :members:
    :undoc-members:

