========
Tortoise
========

.. image:: https://travis-ci.com/tortoise/tortoise-orm.svg?branch=master
    :target: https://travis-ci.com/tortoise/tortoise-orm
.. image:: https://coveralls.io/repos/github/tortoise/tortoise-orm/badge.svg
    :target: https://coveralls.io/github/tortoise/tortoise-orm

Introduction
============
Tortoise is easy-to-use asyncio ORM inspired by Django.

It is built with relations between models in mind and provides simple api for it, that gives you potential for building web services with easy abstractions.

You can find docs at `ReadTheDocs <http://tortoise-orm.readthedocs.io/en/latest/>`_

.. note::

    Tortoise is young project and breaking changes without following semantic versioning are to be expected


Getting Started
===============

Installation
------------
First you have to install tortoise like this:

.. code-block:: bash

    pip install tortoise-orm

Then you should install your db driver

.. code-block:: bash

    pip install asyncpg aiosqlite


Quick Tutorial
--------------

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


After you defined all your models, tortoise needs you to init them, in order to create backward relations between models and match your db client with appropriate models.

You can do it like this:

.. code-block:: python3

    from tortoise import Tortoise
    from tortoise.utils import generate_schema

    async def init():
        # Here we connect to a PostgresQL DB
        # also specify the app name of "models"
        # which contain models from "app.models"
        await Tortoise.init(
            db_url='postgres://postgres:qwerty123@localhost:5432/events',
            modules={'models': ['app.models']}
        )
        # Generate the schema
        await Tortoise.generate_schemas()


Here we create connection to PostgresQL database with default ``asyncpg`` client and then we discover & initialise models.

``generate_schema`` generates schema on empty database, you shouldn't run it on every app init, run it just once, maybe out of your main code.

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
    # (also look for methods .remove(...) and .clear())
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
    # This will fetch all events for team and in those events tournaments will be prefetched
    await Team.all().prefetch_related('events__tournament')
    
    # You can filter and order by related models too
    await Tournament.filter(
        events__name__in=['Test', 'Prod']
    ).order_by('-events__participants__name').distinct()


Contributing
============

Please have a look at the `Contribution Guide <docs/CONTRIBUTING.rst>`_


License
=======

This project is licensed under the Apache License - see the `LICENSE.txt <LICENSE.txt>`_ file for details
