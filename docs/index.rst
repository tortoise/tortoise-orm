========
Tortoise
========

Tortoise is easy-to-use asyncio ORM inspired by Django.

It is built with relations between models in mind and provides simple api for it, that gives you potential for easily building web services with easy abstractions.

.. caution::
   Tortoise is young project and breaking changes without following semantic versioning are to be expected

Features
========

Clean, familiar python interface
--------------------------------
Define your models like so:

.. code-block:: python3

    from tortoise.models import Model
    from tortoise import fields

    class Tournament(Model):
        id = fields.IntField(pk=True)
        name = fields.StringField()

Initialise your models and database like so:

.. code-block:: python3

    from tortoise.backends.sqlite.client import SqliteClient
    from tortoise import Tortoise
    # You must import the models so that Tortoise can discover them
    from app import models 

    async def init():
        db = SqliteClient(db_name)
        await db.create_connection()
        Tortoise.init(db)
        await generate_schema(db)

And use it like so:

.. code-block:: python3

    # Create instance by save
    tournament = Tournament(name='New Tournament')
    await tournament.save()

    # Or by .create()
    await Tournament.create(name='Another Tournament')

    # Now search for a record
    tour = await Tournament.filter(name__contains='Another').first()
    print(tour.name)


Pluggable Database backends
---------------------------
Tortoise currently supports the following databases:

* PostgreSQL (using ``asyncpg``)
* SQLite (using ``aiosqlite``)


Thanks
=======
Huge thanks to https://github.com/kayak/pypika for making this possible.


Table Of Contents
=================

.. toctree::
   :maxdepth: 3

   getting_started
   models_and_fields
   query
   CHANGELOG


If you want to contribute check out issues, or just straightforwardly create PR
