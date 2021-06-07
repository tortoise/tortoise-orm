========
Timezone
========

.. _timezone:

Introduction
============
The design of timezone is inspired by `Django` but also has differences. There are two config items `use_tz` and `timezone` affect timezone in tortois. They can be set in `Tortoise.init` or as global environment variables. 

use_tz
------

When `use_tz = True`, `tortoise` will expect all datetimes to be timezone aware. Which timezone these are stored in the database can be specified with the `timezone` setting. If `timezone` is not set, `UTC` will be used.
When `use_tz = False`, `tortoise` will expect all datetimes to be timezone naive. Thy will be stored in the database without any timezone information. `auto_now` and `auto_now_add` will use `datetime.utcnow()`

timezone
--------
The `timezone` setting determins which datetime `tortoise` will coerce timezone-aware datetimes to. This will also be the timezone that timestamps will be stored with in the database, regardless of which timezone the database is in. You should use `tortoise.timezone.now()` to get timezone-aware time. 

If no `timezone` is set, `UTC` will be used. The `timezone` setting is ineffective when `use_tz = False` as all datetimes are timezone naive. 

Reference
=========

.. automodule:: tortoise.timezone
    :members:
    :undoc-members:

