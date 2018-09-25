Changelog
=========
0.10.7
------
- Fixed SQLite relative db path and :memory: now also works
- Removed confusing error message for missing db driver dependency
- Added ``aiosqlite`` as a required dependency
- ``execute_script()`` now annotates errors just like ``execute_query()``, to reduce confusion
- Bumped ``aiosqlite>=0.6.0`` for performance fix
- Added ``tortoise.run_async()`` helper function to make smaller scripts easier to run. It cleans up connections automatically.
- SQLite does autocommit by default.

0.10.6
------
- Fixed atomic decorator to get connection only on function call

0.10.5
------
- Fixed pre-init queryset objects creation

0.10.4
------
- Added support for running separate transactions in multidb config

0.10.3
------
- Changed default app label from 'models' to None
- Fixed ConfigurationError message for wrong connection name

0.10.2
------
- Set single_connection to True by default, as there is known issues with conection pooling
- Updated documentation

0.10.1
------
- Fixed M2M manager methods to correctly work with transactions
- Fixed mutating of queryset on select queries

0.10.0
------
- Refactored ``Tortoise.init()`` to init all connections and discover models from config passed
  as argument.

  .. caution::
     This is a breaking change.

  You no longer need to import the models module for discovery,
  instead you need to provide an app ⇒ modules map with the init call:

  .. code-block:: python3

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

  For more info, please have a look at :ref:`init_app`

- New ``transactions`` module for implicit working with transactions
- Test frameworks overhauled:
  - Better performance for test runner, using transactions to keep tests isolated.
  - Now depends on an ``initializer()`` and ``finalizer()`` to set up and tear down DB state.
- Exceptions have been further clarified
- Support for CPython 3.7
- Added support for MySQL/MariaDB

0.9.4
-----
- No more asserts, only Tortoise Exceptions
- Fixed PyLint plugin to work with pylint>=2.0.0
- Formalised unittest classes & documented them.
- ``__slots__`` where it was easy to do. (Changes class instances from dicts into tuples, memory savings)

0.9.3
-----
- Fixed backward incompatibility for Python 3.7

0.9.2
-----
- ``JSONField`` is now promoted to a standard field.
- Fixed ``DecimalField`` and ``BooleanField`` to work as expected on SQLite.
- Added ``FloatField``.
- Minimum supported version of PostgreSQL is 9.4
- Added ``.get(...)`` shortcut on query set.
- ``values()`` and ``values_list()`` now converts field values to python types

0.9.1
-----
- Fixed ``through`` parameter honouring for ``ManyToManyField``

0.9.0
-----
- Added support for nested queries for ``values`` and ``values_list``:

.. code-block:: python3

    result = await Event.filter(id=event.id).values('id', 'name', tournament='tournament__name')
    result = await Event.filter(id=event.id).values_list('id', 'participants__name')

- Fixed ``DatetimeField`` and ``DateField`` to work as expected on SQLite.
- Added ``PyLint`` plugin.
- Added test class to mange DB state for testing isolation.

0.8.0
-----
- Added PostgreSQL ``JSONField``

0.7.0
-----
- Added ``.annotate()`` method and basic aggregation funcs

0.6.0
-----
- Added ``Prefetch`` object

0.5.0
-----
- Added ``contains`` and other filter modifiers.
- Field kwarg ``default`` not accepts functions.

0.4.0
-----
- Immutable QuerySet. ``unique`` flag for fields

0.3.0
-----
- Added schema generation and more options for fields:

.. code-block:: python3

    from tortoise import Tortoise
    from tortoise.backends.sqlite.client import SqliteClient
    from tortoise.utils import generate_schema

    client = SqliteClient(db_name)
    await client.create_connection()
    Tortoise.init(client)
    await generate_schema(client)

0.2.0
-----
- Added filtering and ordering by related models fields:

.. code-block:: python3

    await Tournament.filter(
        events__name__in=['1', '3']
    ).order_by('-events__participants__name').distinct()
