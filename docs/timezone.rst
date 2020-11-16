========
Timezone
========

.. _timezone:

Introduction
============
The design of timezone is inspired by `Django` but also has differences. There are two config items `use_tz` and `timezone` affect timezone in tortoise, which can be set when call `Tortoise.init`. And in different DBMS there also are different behaviors.

use_tz
------
When set `use_tz = True`, `tortoise` will always store `UTC` time in database no matter what `timezone` set. And `MySQL` use field type `DATETIME(6)`, `PostgreSQL` use `TIMESTAMPTZ`, `SQLite` use `TIMESTAMP` when generate schema.

timezone
--------
The `timezone` determine what `timezone` is when select datetime field from database, no matter what `timezone` your database is. And you should use `tortoise.timezone.now()` get aware time instead of native time `datetime.datetime.now()`.

Reference
=========

.. automodule:: tortoise.timezone
    :members:
    :undoc-members:

