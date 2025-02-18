.. _getting_started:

===============
Getting started
===============

Installation
===============
The following table shows the available installation options for different databases (note that there are multiple options of clients for some databases):

.. list-table:: Available Installation Options
   :header-rows: 1
   :widths: 30 70

   * - Database
     - Installation Command
   * - SQLite
     - ``pip install tortoise-orm``
   * - PostgreSQL (psycopg)
     - ``pip install tortoise-orm[psycopg]``
   * - PostgreSQL (asyncpg)
     - ``pip install tortoise-orm[asyncpg]``
   * - MySQL (aiomysql)
     - ``pip install tortoise-orm[aiomysql]``
   * - MySQL (asyncmy)
     - ``pip install tortoise-orm[asyncmy]``
   * - MS SQL
     - ``pip install tortoise-orm[asyncodbc]``
   * - Oracle
     - ``pip install tortoise-orm[asyncodbc]``


Optional Dependencies
---------------------
The following libraries can be used to improve performance:

* `orjson <https://pypi.org/project/orjson/>`_: Automatically used if installed for JSON SerDes.
* `uvloop <https://pypi.org/project/uvloop/>`_: Shown to improve performance as an alternative to ``asyncio``.
* `ciso8601 <https://pypi.org/project/ciso8601/>`_: Automatically used if installed.
  Not automatically installed on Windows due to often a lack of a C compiler. Default on Linux/CPython.

The following command will install all optional dependencies:

.. code-block:: bash

    pip install tortoise-orm[accel]
..

Tutorial
========

Define the models by inheriting from ``tortoise.models.Model``.

.. code-block:: python3

    from tortoise.models import Model
    from tortoise import fields

    class Tournament(Model):
        # Defining `id` field is optional, it will be defined automatically
        # if you haven't done it yourself
        id = fields.IntField(primary_key=True)
        name = fields.CharField(max_length=255)


    class Event(Model):
        id = fields.IntField(primary_key=True)
        name = fields.CharField(max_length=255)
        # References to other models are defined in format
        # "{app_name}.{model_name}" - where {app_name} is defined in the tortoise config
        tournament = fields.ForeignKeyField('models.Tournament', related_name='events')
        participants = fields.ManyToManyField('models.Team', related_name='events', through='event_team')


    class Team(Model):
        id = fields.IntField(primary_key=True)
        name = fields.CharField(max_length=255)

.. note::
   You can read more on defining models in :ref:`models`

After defining the models, Tortoise ORM needs to be initialized to establish the relationships between models and connect to the database.
The code below creates a connection to a SQLite DB database with the ``aiosqlite`` client. ``generate_schema`` sets up schema on an empty database.
``generate_schema`` is for development purposes only, see :ref:`migration` for schema migration tools.

.. code-block:: python3

    from tortoise import Tortoise, run_async

    async def main():
        # Here we connect to a SQLite DB file.
        # also specify the app name of "models"
        # which contain models from "app.models
        await Tortoise.init(
            db_url='sqlite://db.sqlite3',
            modules={'models': ['app.models']}
        )
        await Tortoise.generate_schemas()

    run_async(main())


``run_async`` is a helper function to run simple Tortoise scripts. For production use, see :ref:`contrib_fastapi`, :ref:`contrib_sanic` and other integrations, as welll as check out :ref:`cleaningup`.

With the Tortoise initialized, the models are available for use:

.. code-block:: python3

    async def main():
        await Tortoise.init(
            db_url='sqlite://db.sqlite3',
            modules={'models': ['app.models']}
        )
        await Tortoise.generate_schemas()

        # Creating an instance with .save()
        tournament = Tournament(name='New Tournament')
        await tournament.save()

        # Or with .create()
        await Event.create(name='Without participants', tournament=tournament)
        event = await Event.create(name='Test', tournament=tournament)
        participants = []
        for i in range(2):
            team = await Team.create(name='Team {}'.format(i + 1))
            participants.append(team)

        # Many to Many Relationship management is quite straightforward
        # (there are .remove(...) and .clear() too)
        await event.participants.add(*participants)

        # Iterate over related entities with the async context manager
        async for team in event.participants:
            print(team.name)

        # The related entities are cached and can be iterated in the synchronous way afterwards
        for team in event.participants:
            pass

        # Use prefetch_related to fetch related objects
        selected_events = await Event.filter(
            participants=participants[0].id
        ).prefetch_related('participants', 'tournament')
        for event in selected_events:
            print(event.tournament.name)
            print([t.name for t in event.participants])

        # Prefetch multiple levels of related entities
        await Team.all().prefetch_related('events__tournament')

        # Filter and order by related models too
        await Tournament.filter(
            events__name__in=['Test', 'Prod']
        ).order_by('-events__participants__name').distinct()

    run_async(main())

.. note::
    Find more examples (including transactions, using multiple databases and more complex querying) in :ref:`examples` and :ref:`query_api`.
