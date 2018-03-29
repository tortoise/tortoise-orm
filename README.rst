========
Tortoise
========

Introduction
============
Tortoise is easy-to-use asyncio ORM inspired by Django.

It is built with relations between models in mind and provides simple api for it, that gives you potential for easily building web services with easy abstractions.

Disclaimer
==========
Tortoise is young project and breaking changes without following semantic versioning are to be expected

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

Apart from ``asyncpg`` there is also support for ``sqlite`` through ``aiosqlite`` but this driver is rather slow and mainly used for testing. (It is quite easy to implement more backends if there is appropriate asyncio driver for this db)

Tutorial
========

Primary entity of tortoise is ``tortoise.models.Model``.
Sadly, currently tortoise can't generate db schema for you, so first of all you should generate your schema.
Then you can start writing models like this:


.. code-block:: python

    from tortoise.models import Model
    from tortoise import fields

    class Tournament(Model):
        id = fields.IntField(generated=True)
        name = fields.StringField()

        def __str__(self):
            return self.name


    class Event(Model):
        id = fields.IntField(generated=True)
        name = fields.StringField()
        tournament = fields.ForeignKeyField('models.Tournament', related_name='events')
        participants = fields.ManyToManyField('models.Team', related_name='events', through='event_team')

        def __str__(self):
            return self.name


    class Team(Model):
        id = fields.IntField(generated=True)
        name = fields.StringField()

        def __str__(self):
            return self.name

Then in init part of your app you should init models like this (make sure that you **import your models** before calling init):


.. code-block:: python

    from tortoise.backends.asyncpg.client import AsyncpgDBClient
    from tortoise import Tortoise
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


After that you can start using your models:

.. code-block:: python

    # Create instance by save
    tournament = Tournament(name='New Tournament')
    await tournament.save()

    # Or by .create()
    await Event.create(name='Without participants', tournament_id=tournament.id)
    event = await Event.create(name='Test', tournament_id=tournament.id)
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

You can read more examples (including transactions, several databases and a little more complex querying) in ``examples`` directory of this repository

Also
=======

Huge thanks to https://github.com/kayak/pypika for making this possible.

If you want to contribute check out issues, or just straightforwardly create PR
