============
Tortoise ORM
============

Tortoise ORM is an easy-to-use ``asyncio`` ORM *(Object Relational Mapper)* inspired by Django.

.. note::
   Tortoise ORM is a young project and breaking changes are to be expected.
   We keep a `Changelog <https://tortoise.github.io/CHANGELOG.html>`_ and it will have possible breakage clearly documented.

Source & issue trackers are available at `<https://github.com/tortoise/tortoise-orm/>`_

Tortoise ORM supports CPython 3.9 and later for SQLite, MySQL, PostgreSQL, Microsoft SQL Server, and Oracle.

Introduction
============

Why was Tortoise ORM built?
---------------------------

Python has many existing and mature ORMs, unfortunately they are designed with an opposing paradigm of how I/O gets processed.
``asyncio`` is relatively new technology that has a different concurrency model, and the largest change is regarding how I/O is handled.

However, Tortoise ORM is not first attempt of building ``asyncio`` ORM, there are many cases of developers attempting to map synchronous python ORMs to the async world, initial attempts did not have a clean API.

Hence we started Tortoise ORM.

Tortoise ORM is designed to be functional, yet familiar, to ease the migration of developers wishing to switch to ``asyncio``.

It also performs well when compared to other Python ORMs. In `our benchmarks <https://github.com/tortoise/orm-benchmarks>`_, where we measure different read and write operations (rows/sec, more is better), it's trading places with Pony ORM:

.. image:: ORM_Perf.png
    :target: https://github.com/tortoise/orm-benchmarks

How is an ORM useful?
---------------------

An Object-Relational Mapper (ORM) abstracts database interactions, allowing developers to work with databases using high-level, object-oriented code instead of raw SQL.

* Reduces boilerplate SQL, allowing faster development with cleaner, more readable code.
* Helps prevent SQL injection by using parameterized queries.
* Centralized schema and relationship definitions make code easier to manage and modify.
* Handles schema changes through version-controlled migrations.

Features
========

Clean, familiar Python interface
--------------------------------
Model definitions:

.. code-block:: python3

    from tortoise.models import Model
    from tortoise import fields

    class Tournament(Model):
        id = fields.IntField(primary_key=True)
        name = fields.TextField()


Operations on models, queries and complex aggregations:

.. code-block:: python3
    # Creating a record
    await Tournament.create(name='Another Tournament')

    # Searching for a record
    tour = await Tournament.filter(name__contains='Another').first()
    print(tour.name)

    # Count groups of records with a complex condition
    await Tournament.annotate(
        name_prefix=Case(
            When(name__startswith="One", then="1"),
            When(name__startswith="Two", then="2"),
            default="0",
        ),
    ).annotate(
        count=Count(F("name_prefix")),
    ).group_by(
        "name_prefix"
    ).values("name_prefix", "count")


See :ref:`getting_started` for a more detailed guide.


Pluggable Database backends
---------------------------
Tortoise ORM currently supports the following :ref:`databases`:

* `PostgreSQL` >= 9.4 (using ``asyncpg``)
* `SQLite` (using ``aiosqlite``)
* `MySQL`/`MariaDB` (using `asyncmy <https://github.com/long2ice/asyncmy>`_)
* `Microsoft SQL Server`/`Oracle` (using ``asyncodbc``)

And more
--------

Tortoise ORM supports the following features:

* Composable, Django-inspired :ref:`models`
* Supports relations, such as ``ForeignKeyField`` and ``ManyToManyField``
* Supports many standard :ref:`fields`
* Comprehensive :ref:`query_api`
* Transactions :ref:`transactions`
* Supports tests frameworks, see :ref:`unittest`
* :ref:`pylint`

If you want to contribute, check out issues first, and then create a PR.
