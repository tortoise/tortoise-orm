========
Timezone
========

.. _timezone:

Introduction
============
The design of timezone is inspired by `Django` but also has differences. There are two config items `use_tz` and `timezone` affect timezone in tortoise, which can be set when call `Tortoise.init`. And in different DBMS there also are different behaviors.

.. note::

    As of 1.0, ``pytz`` has been removed. Timezone handling uses Python's standard library
    ``zoneinfo`` module. All timezone objects returned by Tortoise are ``ZoneInfo`` instances.

use_tz
------
``use_tz`` defaults to ``True``. When enabled, all datetimes are stored as UTC in the database and ``tortoise.timezone.now()`` returns a timezone-aware datetime. ``MySQL`` uses ``DATETIME(6)``, ``PostgreSQL`` uses ``TIMESTAMPTZ``, and ``SQLite`` uses ``TIMESTAMP`` for schema generation.
For ``TimeField``, ``MySQL`` uses ``TIME(6)``, ``PostgreSQL`` uses ``TIMETZ``, and ``SQLite`` uses ``TIME``.

When ``use_tz = False``, datetimes are stored and returned as naive (no timezone info). ``tortoise.timezone.now()`` returns a naive datetime in this mode.

timezone
--------
The ``timezone`` setting determines what timezone is used when reading ``DateTimeField`` and ``TimeField`` from the database (only effective when ``use_tz = True``). Use ``tortoise.timezone.now()`` to get the current time respecting your ``use_tz`` setting.

Reference
=========

.. automodule:: tortoise.timezone
    :members:
    :undoc-members:
