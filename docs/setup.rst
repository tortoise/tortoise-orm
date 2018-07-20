======
Set up
======

Init app
========

After you defined all your models, tortoise needs you to init them, in order to create backward relations between models and match your db client with appropriate models.

You can do it like this:

.. code-block:: python3

    from tortoise.backends.asyncpg.client import AsyncpgDBClient
    from tortoise import Tortoise
    from app import models # without importing models Tortoise can't find and init them


    async def init():
        db = AsyncpgDBClient(
            host='localhost',
            port=5432,
            user='postgres',
            password='qwerty123',
            database='events',
       )

        await db.create_connection()
        Tortoise.init(db)

        await generate_schema(client)

Here we create connection to database with default ``asyncpg`` client and then we ``init()`` models. Be sure that you have your models imported in the app. Usually that's the case, because you use your models across you app, but if you have only local imports of it, tortoise won't be able to find them and init them with connection to db.
``generate_schema`` generates schema on empty database, you shouldn't run it on every app init, run it just once, maybe out of your main code.

