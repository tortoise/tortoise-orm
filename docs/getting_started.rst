.. _getting_started:

===============
Getting started
===============

Installation
===============
First you have to install tortoise like this:

.. code-block:: bash

    pip install tortoise-orm

..

You can also install with your db driver:

.. code-block:: bash

    pip install tortoise-orm[asyncpg]

..

Or MySQL:

.. code-block:: bash

    pip install tortoise-orm[aiomysql]

..

Apart from ``asyncpg`` there is also support for ``sqlite`` through ``aiosqlite`` and
``mysql`` through ``aiomysql``.
You can easily implement more backends if there is appropriate ``asyncio`` driver for this db.

Optional Accelerators
---------------------
The following libraries can be used as accelerators:

* `python-rapidjson <https://pypi.org/project/python-rapidjson/>`_: Automatically used if installed for JSON SerDes.
* `uvloop <https://pypi.org/project/uvloop/>`_: Shown to improve performance, but needs to be set up.
  Please look at ``uvloop`` documentation for more info.
  If you use a framework, it may already use it.
* `ciso8601 <https://pypi.org/project/ciso8601/>`_: Automatically used if installed.
  Not automatically installed on Windows due to often a lack of a C compiler. Default on Linux/CPython.

You can install with all accelerators above:

.. code-block:: bash

    pip install tortoise-orm[accel]

..

Tutorial
========

Primary entity of tortoise is ``tortoise.models.Model``.
You can start writing models like this:


.. code-block:: python3

    from tortoise.models import Model
    from tortoise import fields

    class Tournament(Model):
        # Defining `id` field is optional, it will be defined automatically
        # if you haven't done it yourself
        id = fields.IntField(pk=True)
        name = fields.CharField(max_length=255)

        # Defining ``__str__`` is also optional, but gives you pretty
        # represent of model in debugger and interpreter
        def __str__(self):
            return self.name


    class Event(Model):
        id = fields.IntField(pk=True)
        name = fields.CharField(max_length=255)
        # References to other models are defined in format
        # "{app_name}.{model_name}" - where {app_name} is defined in tortoise config
        tournament = fields.ForeignKeyField('models.Tournament', related_name='events')
        participants = fields.ManyToManyField('models.Team', related_name='events', through='event_team')

        def __str__(self):
            return self.name


    class Team(Model):
        id = fields.IntField(pk=True)
        name = fields.CharField(max_length=255)

        def __str__(self):
            return self.name

.. note::
   You can read more on defining models in :ref:`models`

After you defined all your models, tortoise needs you to init them, in order to create backward relations between models and match your db client with appropriate models.

You can do it like this:

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


Here we create connection to PostgresQL database with default ``asyncpg`` client and then we discover & initialise models.

``generate_schema`` generates schema on empty database, you shouldn't run it on every app init, run it just once, maybe out of your main code.

If you are running this in a simple script, you can do:

.. code-block:: python3

    run_async(init())

``run_async`` is a helper function to run simple async Tortoise scripts. If you are running Tortoise ORM as part of a service, please have a look at :ref:`cleaningup`

After that you can start using your models:

.. code-block:: python3

    # Create instance by save
    tournament = Tournament(name='New Tournament')
    await tournament.save()

    # Or by .create()
    await Event.create(name='Without participants', tournament=tournament)
    event = await Event.create(name='Test', tournament=tournament)
    participants = []
    for i in range(2):
        team = await Team.create(name='Team {}'.format(i + 1))
        participants.append(team)

    # M2M Relationship management is quite straightforward
    # (look for methods .remove(...) and .clear())
    await event.participants.add(*participants)

    # You can query related entity just with async for
    async for team in event.participants:
        pass

    # After making related query you can iterate with regular for,
    # which can be extremely convenient for using with other packages,
    # for example some kind of serializers with nested support
    for team in event.participants:
        pass


    # Or you can make preemptive call to fetch related objects,
    # so you can work with related objects immediately
    selected_events = await Event.filter(
        participants=participants[0].id
    ).prefetch_related('participants', 'tournament')
    for event in selected_events:
        print(event.tournament.name)
        print([t.name for t in event.participants])

    # Tortoise ORM supports variable depth of prefetching related entities
    # This will fetch all events for team and in those team tournament will be prefetched
    await Team.all().prefetch_related('events__tournament')

    # You can filter and order by related models too
    await Tournament.filter(
        events__name__in=['Test', 'Prod']
    ).order_by('-events__participants__name').distinct()

.. note::
    You can read more examples (including transactions, several databases and a little more complex querying) in
    :ref:`examples`
