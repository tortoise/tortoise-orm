===============
Getting started
===============


Installation
===============
First you have to install tortoise like this:

.. code-block:: bash

    pip install tortoise-orm

..

Then you should install your db driver

.. code-block:: bash

    pip install asyncpg

..

Apart from ``asyncpg`` there is also support for ``sqlite`` through ``aiosqlite``.
It is quite easy to implement more backends if there is appropriate asyncio driver for this db.

Tutorial
========

Primary entity of tortoise is ``tortoise.models.Model``.
You can start writing models like this:


.. code-block:: python3

    from tortoise.models import Model
    from tortoise import fields
    
    class Tournament(Model):
        id = fields.IntField(pk=True)
        name = fields.TextField()
    
        def __str__(self):
            return self.name


    class Event(Model):
        id = fields.IntField(pk=True)
        name = fields.TextField()
        tournament = fields.ForeignKeyField('models.Tournament', related_name='events')
        participants = fields.ManyToManyField('models.Team', related_name='events', through='event_team')
    
        def __str__(self):
            return self.name


    class Team(Model):
        id = fields.IntField(pk=True)
        name = fields.TextField()
    
        def __str__(self):
            return self.name

Then in init part of your app you should init models like this
(make sure that you **import your models** before calling init, tortoise must see them to init normally):


.. code-block:: python3

    from tortoise.backends.asyncpg.client import AsyncpgDBClient
    from tortoise import Tortoise
    from tortoise.utils import generate_schema
    from app import models # without importing models Tortoise can't find and init them


    async def init():
        db = AsyncpgDBClient(
            host='localhost',
            port=5432,
            user='postgres',
            password='qwerty123',
            database='events'
        )
    
        await db.create_connection()
        Tortoise.init(db)
        # You can generate schema for your models like this, but don't do this if you have schema already:
        await generate_schema(db)

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
        team = Team.create(name='Team {}'.format(i + 1))
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


    # Or you can make preemptive call to fetch related objects
    selected_events = await Event.filter(
        participants=participants[0].id
    ).prefetch_related('participants', 'tournament')
    
    # Tortoise supports variable depth of prefetching related entities
    # This will fetch all events for team and in those team tournament will be prefetched
    await Team.all().prefetch_related('events__tournament')
    
    # You can filter and order by related models too
    await Tournament.filter(
        events__name__in=['Test', 'Prod']
    ).order_by('-events__participants__name').distinct()

You can read more examples (including transactions, several databases and a little more complex querying) in
`examples <https://github.com/Zeliboba5/tortoise-orm/tree/master/examples>`_ directory of this repository


