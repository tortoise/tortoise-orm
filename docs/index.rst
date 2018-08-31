========
Tortoise
========

Tortoise is easy-to-use asyncio ORM inspired by Django.

It is built with relations between models in mind and provides simple api for it, that gives you potential for easily building web services with easy abstractions.

.. caution::
   Tortoise is young project and breaking changes without following semantic versioning are to be expected

Source & issue trackers are available at `<https://github.com/tortoise/tortoise-orm/>`_

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
        name = fields.TextField()

Initialise your models and database like so:

.. code-block:: python3

    from tortoise import Tortoise

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
Tortoise currently supports the following :ref:`databases`:

* PostgreSQL >= 9.4 (using ``asyncpg``)
* SQLite (using ``aiosqlite``)
* MySQL/MariaDB (using ``aiomysql``)


And more
--------

Tortoise-ORM supports the following features:

* Designed to be used in an existing project:
    * Testing framework uses existing Python Unittest framework, just requires
      that ``initializer()`` and ``finalizer()`` gets called to set up and tear
      down the test databases. (See :ref:`unittest`)
    * ORM :ref:`init_app` configures entierly from provided parameters
* Composable, Django-inspired :ref:`models`
* Supports relations, such as ``ForeignKeyField`` and ``ManyToManyField``
* Supports many standard :ref:`fields`
* Comprehensive :ref:`query_api`
* :ref:`pylint`

If you want to contribute check out issues, or just straightforwardly create PR
