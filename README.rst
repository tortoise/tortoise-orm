============
Tortoise ORM
============

.. image:: https://img.shields.io/pypi/v/tortoise-orm.svg?style=flat
   :target: https://pypi.python.org/pypi/tortoise-orm
.. image:: https://pepy.tech/badge/tortoise-orm/month
   :target: https://pepy.tech/project/tortoise-orm
.. image:: https://github.com/tortoise/tortoise-orm/workflows/gh-pages/badge.svg
   :target: https://github.com/tortoise/tortoise-orm/actions?query=workflow:gh-pages
.. image:: https://github.com/tortoise/tortoise-orm/actions/workflows/ci.yml/badge.svg?branch=develop
   :target: https://github.com/tortoise/tortoise-orm/actions?query=workflow:ci
.. image:: https://coveralls.io/repos/github/tortoise/tortoise-orm/badge.svg
   :target: https://coveralls.io/github/tortoise/tortoise-orm
.. image:: https://app.codacy.com/project/badge/Grade/844030d0cb8240d6af92c71bfac764ff
   :target: https://www.codacy.com/gh/tortoise/tortoise-orm/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=tortoise/tortoise-orm&amp;utm_campaign=Badge_Grade

Introduction
============

Tortoise ORM is an easy-to-use ``asyncio`` ORM *(Object Relational Mapper)* inspired by Django.

Tortoise ORM was built with relations in mind and admiration for the excellent and popular Django ORM.
It's engraved in its design that you are working not with just tables, you work with relational data.

You can find the docs at `Documentation <https://tortoise.github.io>`_

.. note::
   Tortoise ORM is a young project and breaking changes are to be expected.
   We keep a `Changelog <https://tortoise.github.io/CHANGELOG.html>`_ and it will have possible breakage clearly documented.

Tortoise ORM is supported on CPython >= 3.8 for SQLite, MySQL and PostgreSQL and Microsoft SQL Server and Oracle.

Why was Tortoise ORM built?
---------------------------

Python has many existing and mature ORMs, unfortunately they are designed with an opposing paradigm of how I/O gets processed.
``asyncio`` is relatively new technology that has a very different concurrency model, and the largest change is regarding how I/O is handled.

However, Tortoise ORM is not the first attempt of building an ``asyncio`` ORM. While there are many cases of developers attempting to map synchronous Python ORMs to the async world, initial attempts did not have a clean API.

Hence we started Tortoise ORM.

Tortoise ORM is designed to be functional, yet familiar, to ease the migration of developers wishing to switch to ``asyncio``.

It also performs well when compared to other Python ORMs. In `our benchmarks <https://github.com/tortoise/orm-benchmarks>`_, where we measure different read and write operations (rows/sec, more is better), it's trading places with Pony ORM:

.. image:: https://raw.githubusercontent.com/tortoise/tortoise-orm/develop/docs/ORM_Perf.png
    :target: https://github.com/tortoise/orm-benchmarks

How is an ORM useful?
---------------------

When you build an application or service that uses a relational database, there is a point where you can't get away with just using parameterized queries or even query builder. You just keep repeating yourself, writing slightly different code for each entity.
Code has no idea about relations between data, so you end up concatenating your data almost manually.
It is also easy to make mistakes in how you access your database, which can be exploited by SQL-injection attacks.
Your data rules are also distributed, increasing the complexity of managing your data, and even worse, could lead to those rules being applied inconsistently.

An ORM (Object Relational Mapper) is designed to address these issues, by centralising your data model and data rules, ensuring that your data is managed safely (providing immunity to SQL-injection) and keeping track of relationships so you don't have to.

Getting Started
===============

Installation
------------
First you have to install Tortoise ORM like this:

.. code-block:: bash

    pip install tortoise-orm

You can also install with your db driver (`aiosqlite` is builtin):

.. code-block:: bash

    pip install "tortoise-orm[asyncpg]"


For `MySQL`:

.. code-block:: bash

    pip install "tortoise-orm[asyncmy]"

For `Microsoft SQL Server`/`Oracle` (**not fully tested**):

.. code-block:: bash

    pip install "tortoise-orm[asyncodbc]"

Quick Tutorial
--------------

The primary entity of tortoise is ``tortoise.models.Model``.
You can start writing models like this:


.. code-block:: python3

    from tortoise.models import Model
    from tortoise import fields

    class Tournament(Model):
        id = fields.IntField(primary_key=True)
        name = fields.TextField()

        def __str__(self):
            return self.name


    class Event(Model):
        id = fields.IntField(primary_key=True)
        name = fields.TextField()
        tournament = fields.ForeignKeyField('models.Tournament', related_name='events')
        participants = fields.ManyToManyField('models.Team', related_name='events', through='event_team')

        def __str__(self):
            return self.name


    class Team(Model):
        id = fields.IntField(primary_key=True)
        name = fields.TextField()

        def __str__(self):
            return self.name


After you defined all your models, tortoise needs you to init them, in order to create backward relations between models and match your db client with the appropriate models.

You can do it like this:

.. code-block:: python3

    from tortoise import Tortoise

    async def init():
        # Here we connect to a SQLite DB file.
        # also specify the app name of "models"
        # which contain models from "app.models"
        await Tortoise.init(
            db_url='sqlite://db.sqlite3',
            modules={'models': ['app.models']}
        )
        # Generate the schema
        await Tortoise.generate_schemas()


Here we create a connection to an SQLite database in the local directory called ``db.sqlite3``. Then we discover and initialise the models.

Tortoise ORM currently supports the following databases:

* `SQLite` (requires ``aiosqlite``)
* `PostgreSQL` (requires ``asyncpg``)
* `MySQL` (requires ``asyncmy``)
* `Microsoft SQL Server`/`Oracle` (requires ``asyncodbc``)

``generate_schema`` generates the schema on an empty database. Tortoise generates schemas in safe mode by default which
includes the ``IF NOT EXISTS`` clause, so you may include it in your main code.


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
    # (also look for methods .remove(...) and .clear())
    await event.participants.add(*participants)

    # You can query a related entity with async for
    async for team in event.participants:
        pass

    # After making a related query you can iterate with regular for,
    # which can be extremely convenient when using it with other packages,
    # for example some kind of serializers with nested support
    for team in event.participants:
        pass


    # Or you can make a preemptive call to fetch related objects
    selected_events = await Event.filter(
        participants=participants[0].id
    ).prefetch_related('participants', 'tournament')

    # Tortoise supports variable depth of prefetching related entities
    # This will fetch all events for Team and in those events tournaments will be prefetched
    await Team.all().prefetch_related('events__tournament')

    # You can filter and order by related models too
    await Tournament.filter(
        events__name__in=['Test', 'Prod']
    ).order_by('-events__participants__name').distinct()

Migration
=========

Tortoise ORM uses `Aerich <https://github.com/tortoise/aerich>`_ as its database migration tool, see more detail at its `docs <https://github.com/tortoise/aerich>`_.

Contributing
============

Please have a look at the `Contribution Guide <docs/CONTRIBUTING.rst>`_.

ThanksTo
========

Powerful Python IDE `Pycharm <https://www.jetbrains.com/pycharm/>`_
from `Jetbrains <https://jb.gg/OpenSourceSupport>`_.

.. image:: https://resources.jetbrains.com/storage/products/company/brand/logos/jb_beam.svg
    :target: https://jb.gg/OpenSourceSupport

License
=======

This project is licensed under the Apache License - see the `LICENSE.txt <LICENSE.txt>`_ file for details.
