.. _changelog:

Changelog
=========
0.15.7
------
- ``QuerySet.Update()`` now returns the count of the no of rows affected. Note, that
- ``QuerySet.Delete()`` now returns the count of the no of rows deleted.
- Note that internal API of ``db_connection.execute_query()`` now returns ``rows_affected, results``. (This is informational only)
- Added ``get_or_none(...)`` as syntactic sugar for ``filter(...).first()``

0.15.6
------
- Added ``BinaryField`` for storing binary objects (``bytes``).
- Changed ``TextField`` to use ``LONGTEXT`` for MySQL to allow for larger than 64KB of text.
- De-duplicate index if specified on both ``index=true`` and as part of ``indexes``
- Primary Keyed ``TextField`` is marked as deprecated.
  We can't guarnatee that it will be properly indexed or unique in all cases.
- One can now disable the backwards relation for FK/O2O relations by passing ``related_name=False``
- One can now pass a PK value to a generated field, and Tortoise ORM will use that as the PK as expected.
  This allows one to have a model that has a autonumber PK, but setting it explicitly if required.

0.15.5
------
* Refactored Fields:

  Fields have been refactored, for better maintenance. There should be no change for most users.

  - More accurate auto-completion.
  - Fields now contain their own SQL schema by dialect, which significantly simplifies adding field types.
  - ``describe_model()`` now returns the DB type, and dialect overrides.

- ``JSONField`` will now automatically use ``python-rapidjson`` as an accelerator if it is available.
- ``DecimalField`` and aggregations on it, now behaves much more like expected on SQLite (#256)
- Check whether charset name is valid for the MySQL connection (#261)
- Default DB driver parameters are now applied consistently, if you use the URI schema or manual.

0.15.4
------
- Don't generate a schema if there is no models (#254)
- Emit a ``RuntimeWarning`` when a module has no models to import (#254)
- Allow passing in a custom SSL context (#255)

0.15.3
------
* Added ``OneToOneField`` implementation:

  ``OneToOneField`` describes a one to one relation between two models.
  It can be set from the primary side only, but resolved from both sides in the same way.

  ``describe_model(...)`` now also reports OneToOne relations in both directions.

  Usage example:

  .. code-block:: python3

     event: fields.OneToOneRelation[Event] = fields.OneToOneField(
         "models.Event", on_delete=fields.CASCADE, related_name="address"
     )

- Prefetching is done concurrently now, sending all prefetch requests at the same time instead of in sequence.
- Enabe foreign key enforcement on SQLite for builds where it was optional.

0.15.2
------
- The ``auto_now_add`` argument of ``DatetimeField`` is handled correctly in the SQLite backend.
- ``unique_together`` now creates named constrains, to prevent the DB from auto-assigning a potentially non-unique constraint name.
- Filtering by an ``auto_now`` field doesn't replace the filter value with ``now()`` anymore.

0.15.1
------
- Handle OR'ing a blank ``Q()`` correctly (#240)

0.15.0
-------
New features:
^^^^^^^^^^^^^
- Pooling has been implemented, allowing for multiple concurrent databases and all the benefits that comes with it.
    - Enabled by default for databases that support it (mysql and postgres) with a minimum pool size of 1, and a maximum of 5
    - Not supported by sqlite
    - Can be changed by passing the ``minsize`` and ``maxsize`` connection parameters
- Many small performance tweaks:
    - Overhead of query generation has been reduced by about 6%
    - Bulk inserts are ensured to be wrapped in a transaction for >50% speedup
    - PostgreSQL prepared queries now use a LRU cache for significant >2x speedup on inserts/updates/deletes
- ``DateField`` & ``DatetimeField`` deserializes faster on PostgreSQL & MySQL.
- Optimized ``.values()`` to do less copying, resulting in a slight speedup.
- One can now pass kwargs and ``Q()`` objects as parameters to ``Q()`` objects simultaneously.

Bugfixes:
^^^^^^^^^
- ``indexes`` will correctly map the foreign key if referenced by name.
- Setting DB generated PK in constructor/create generates exception instead of silently being ignored.

Deprecations:
^^^^^^^^^^^^^
- ``start_transaction`` is deprecated, please use ``@atomic()`` or ``async with in_transaction():`` instead.
- **This release brings with it, deprecation of Python 3.6 / PyPy-3.6:**

  This is due to small differences with how the backported ``aiocontextvars`` behaves
  in comparison to the built-in in Python 3.7+.

  There is a known context confusion, specifically regarding nested transactions.

0.14.2
------
- A Field name of ``alias`` is now no longer reserved.
- Restored support for inheriting from Abstract classes. Order is now also deterministic,
  with the inherited classes' fields being placed before the current.

0.14.1
-------
- ``ManyToManyField`` is now a function that has the type of the relation for autocomplete,
  this allows for better type hinting at less effort.
- Added section on adding better autocomplete for relations in editors.

0.14.0
------
.. caution::
   **This release drops support of Python 3.5:**

   Tortoise ORM now requires a minimum of CPython 3.6 or PyPy3.6-7.1

Enhancements:
^^^^^^^^^^^^^
- Models, Fields & QuerySets have significant type annotation improvements,
  leading to better IDE integration and more comprehensive static analysis.
- Fetching records from the DB is now up to 25% faster.
- Database functions ``Trim()``, ``Length()``, ``Coalesce()``, ``Lower()``, ``Upper()`` added to tortoise.functions module.
- Annotations can be selected inside ``Queryset.values()`` and ``Queryset.values_list()`` expressions.
- Added support for Python 3.8
- The Foreign Key property is now ``await``-able as long as one didn't populate it via ``.prefetch_related()``
- One can now specify compound indexes in the ``Meta:`` class using ``indexes``. It works just like ``unique_toghether``.

Bugfixes:
^^^^^^^^^
- The generated index name now has significantly lower chance of collision.
- The compiled SQL query contains HAVING and GROUP BY only for aggregation functions.
- Fields for FK relations are quoted properly.
- Fields are quoted properly in ``UNIQUE`` statements.
- Fields are quoted properly in ``KEY`` statements.
- Comment Fields are quoted properly in PostgreSQL dialect.
- ``unique_together`` will correctly map the foreign key if referenced by name.

Deprecations:
^^^^^^^^^^^^^
- ``import from tortoise.aggregation`` is deprecated, please do ``import from tortoise.functions`` instead.

Breaking Changes:
^^^^^^^^^^^^^^^^^
- The hash used to make generated indexes unique has changed.
  The old algorithm had a very high chance of collisions,
  the new hash algorithm is much better in this regard.
- Dropped support for Python 3.5


0.13.12
-------
- Reverted "The ``Field`` class now calls ``super().__init__``, so mixins are properly initialised."
  as it was causing issues on Python 3.6.

0.13.11
-------
- Fixed the ``_FieldMeta`` class not to checking if the 1st base class was Field, so would break with mixins.
- The ``Field`` class now calls ``super().__init__``, so mixins are properly initialised.

0.13.10
-------
- Names ForeignKey constraints in a consistent way

0.13.9
------
- Fields can have 2nd base class which makes IDEs know python type (str, int, datetime...) of the field.
- The ``type`` parameter of ``Field.__init__`` is removed, instead we use the 2nd base class
- Foreign keys and indexes are now defined correctly in MySQL so that they take effect as expected
- MySQL now doesn't warn of unsafe index creation anymore

0.13.8
------
- Fixed bug in schema creation for MySQL where non-int PK did not get declared properly (#195)

0.13.7
------
- ``iexact`` filter modifier was implemented. Queries like ``«queryset».filter(name__iexact=...)`` will perform case-insensitive search.

0.13.6
------
- Fix minor bug in ``Model.__init__`` where we raise the wrong error on setting RFK/M2M values directly.
- Fields in ``Queryset.values_list()`` is now in the defined Model order.
- Fields in ``Queryset.values()`` is now in the defined Model order.

0.13.5
------
- Sample Starlette integration
- Relational fields are now lazily constructed via properties instead of in the constructor,
  this results in a significant overhead reduction for Model instantiation with many relationships.

0.13.4
------
- Assigning to the FK field will correctly set the associated db-field
- Reading a nullalble FK field can now be None
- Nullalble FK fields reverse-FK is now also nullable
- Deleting a nullable FK field sets it to None

0.13.3
------
- Fixed installing Tortoise-ORM in non-unicode systems. (#180)
- ``«queryset».update(…)`` now correctly uses the DB-specific ``to_db_value()``
- ``fetch_related(…)`` now correctly encodes non-integer keys.
- ``ForeignKey`` fields of type ``UUIDField`` are now escaped consistently.
- Pre-generated ForeignKey fields (e.g. UUIDField) is now checked for persistence correctly.
- Duplicate M2M ``.add(…)`` now checks using consistent field encoding.
- ``source_field`` Fields are now handled correctly for ordering.
- ``source_field`` Fields are now handled correctly for updating.

0.13.2
------
* Security fixes for ``«model».save()`` & ``«model».delete()``:

  This is now fully parametrized, and these operations are no longer susceptible to escaping issues.

* Performance improvements:

  - Simple update is now ~3-6× faster
  - Partial update is now ~3× faster
  - Delete is now ~2.7x faster

- Fix generated Schema Primary Key for ``BigIntField`` for MySQL and PostgreSQL.
- Added support for using a ``SmallIntField`` as a auto-gen Primary Key.
- Ensure that default PK is added to the top of the attrs.

0.13.1
------
* Model schema now has a discovery API:

  One can call ``Tortoise.describe_models()`` or ``Tortoise.describe_model(<Model>)`` to get
  a full description of the model(s).

  Please see :meth:`tortoise.Tortoise.describe_model` and :meth:`tortoise.Tortoise.describe_models` for more info.

- Fix in generating comments for Foreign Keys in ``MySQL``
- Added schema support for PostgreSQL. Either set  ``"schema": "custom"`` var in ``credentials`` or as a query parameter ``?schema=custom``
- Default MySQL charset to ``utf8mb4``. If a charset is provided it will also force the TABLE charset to the same.

0.13.0
------
.. warning::
   **This release brings with it, deprecation of Python 3.5:**

   We will increase the minimum supported version of Python to 3.6,
   as 3.5 is reaching end-of-life,
   and is missing many useful features for async applications.

   We will discontinue Python 3.5 support on the next major release (Likely 0.14.0)

New Features:
^^^^^^^^^^^^^
- Example Sanic integration along with register_tortoise hook in contrib (#163)
- ``.values()`` and ``.values_list()`` now default to all fields if none are specified.
- ``generate_schema()`` now generates well-formatted DDL SQL statements.
- Added ``TruncationTestCase`` testing class that truncates tables to allow faster testing of transactions.
- Partial saves are now supported (#157): ``obj.save(update_fields=['model','field','names'])``

Bugfixes:
^^^^^^^^^
- Fixed state leak between database drivers which could cause incorrect DDL generation.
- Fixed missing table/column comment generation for ``ForeignKeyField`` and ``ManyToManyField``
- Fixed comment generation to escape properly for ``SQLite``
- Fixed comment generation for ``PostgreSQL`` to not duplicate comments
- Fixed generation of schema for fields that defined custom ``source_field`` values defined
- Fixed working with Models that have fields with custom ``source_field`` values defined
- Fixed safe creation of M2M tables for MySQL dialect (#168)

Docs/examples:
^^^^^^^^^^^^^^
- Examples have been reworked:

  - Simplified init of many examples
  - Re-did ``generate_schema.py`` example
  - A new ``relations_recirsive.py`` example (turned into test case)

- Lots of small documentation cleanups

0.12.7 (retracted)
------------------
- Support connecting to PostgreSQL via Unix domain socket (simple case).
- Self-referential Foreign and Many-to-Many keys are now allowed

0.12.6 / 0.12.8
---------------
* Handle a ``__models__`` variable within modules to override the model discovery mechanism.

    If you define the ``__models__`` variable in ``yourapp.models`` (or wherever you specify to load your models from),
    ``generate_schema()`` will use that list, rather than automatically finding all models for you.

- Split model consructor into from-Python and from-DB paths, leading to 15-25% speedup for large fetch operations.
- More efficient queryset manipulation, 5-30% speedup for small fetches.

0.12.5
------
- Using non registered models or wrong references causes an ConfigurationError with a helpful message.

0.12.4
------
- Inherit fields from Mixins, together with abstract model classes.

0.12.3
------
- Added description attribute to Field class. (#124)
- Added the ability to leverage field description from (#124) to generate table column comments and ability to add table level comments

0.12.2
------
- Fix accidental double order-by for ``.values()`` based queries. (#143)

0.12.1
------
* Bulk insert operation:

  .. note::
     The bulk insert operation will do the minimum to ensure that the object
     created in the DB has all the defaults and generated fields set,
     this may result in incomplete references in Python.

     e.g. ``IntField`` primary keys will not be populated.

  This is recommend only for throw away inserts where you want to ensure optimal
  insert performance.

  .. code-block:: python3

      User.bulk_create([
          User(name="...", email="..."),
          User(name="...", email="...")
      ])

- Notable efficiency improvement for regular inserts

0.12.0
------
* Tortoise ORM now supports non-autonumber primary keys.

  .. note::
     This is a big feature change. It should not break any existing implementations.

  That primary key will be accesible through a reserved field ``pk`` which will be an alias of whichever field has been nominated as a primary key.
  That alias field can be used as a field name when doing filtering e.g. ``.filter(pk=...)`` etc…

  We currently support single (non-composite) primary keys of any indexable field type, but only these field types are recommended:

  .. code-block:: python3

      IntField
      BigIntField
      CharField
      UUIDField

  One must define a primary key by setting a ``pk`` parameter to ``True``.

  If you don't define a primary key, we will create a primary key of type ``IntField`` with name of ``id`` for you.

  Any of these are valid primary key definitions in a Model:

  .. code-block:: python3

      id = fields.IntField(pk=True)

      checksum = fields.CharField(pk=True)

      guid = fields.UUIDField(pk=True)


0.11.13
-------
- Fixed connection retry to work with transactions
- Added broader PostgreSQL connection failiure detection

0.11.12
-------
- Added automatic PostgreSQL connection retry

0.11.11
-------
- Extra parameters now get passed through to the MySQL & PostgreSQL drivers

0.11.10
-------
- Fixed SQLite handling of DatetimeField

0.11.9
------
- Code has been reformatted using ``black``, and minor code cleanups (#120 #123)
- Sample Quart integration (#121)
- Better isolation of connection handling — Allows more dynamic connections so we can do pooling & reconnections.
- Added automatic MySQL connection retry

0.11.8
------
- Fixed ``.count()`` when a join happens (#109)

0.11.7
------
- Fixed ``unique_together`` for foreign keys (#114)
- Fixed Field.to_db_value method to handle Enum (#113 #115 #116)

0.11.6
------
- Added ability to use ``unique_together`` meta Model option

0.11.5
------
- Fixed concurrency isolation when attempting to do multiple concurrent operations on a single connection.

0.11.4
------
- Fixed several convenience issues with foreign relations:

  - FIXED: ``.all()`` actually returns the _query property as was documented.
  - New models with FK don't automatically fail to resolve any data. They can now be evaluated lazily.

- Some DB's don't support OFFSET without Limit, added caps to signal workaround, which is to automatically add limit of 1000000
- Pylint plugin to know about default ``related_name`` for ForeignKey fields.
- Simplified capabilities to be static, and defined at class level.

0.11.3
------
* Added basic DB driver Capabilities.

  Test runner now has the ability to skip tests conditionally, based on the DB driver Capabilities:

  .. code-block:: python3

      @requireCapability(dialect='sqlite')
      async def test_run_sqlite_only(self):
          ...

* Added per-field indexes.

  When setting ``index=True`` on a field, Tortoise will now generate an index for it.

  .. note::
     Due to MySQL limitation of not supporting conditional index creation,
     if ``safe=True`` (the default) is set, it won't create the index and emit a warning about it.

     We plan to work around this limitation in a future release.

- Performance fix with PyPika for small fetch queries
- Remove parameter hack now that PyPika support Parametrized queries
- Fix typos in JSONField docstring
- Added ``.explain()`` method on ``QuerySet``.
- Add ``required`` read-only property to fields

0.11.2
------
- Added "safe" schema generation
- Correctly convert values to their db representation when using the "in" filter
- Added some common missing field types:

  - ``BigIntField``
  - ``TimeDeltaField``

- ``BigIntField`` can also be used as a primary key field.

0.11.1
------
- Test class isolation fixes & contextvars update
- Turned on autocommit for MySQL
- db_url now supports defaults and casting parameters to the right types

0.11.0
------
- Added ``.exclude()`` method for QuerySet
- Q objects can now be negated for ``NOT`` query (``~Q(...)``)
- Support subclassing on existing fields
- Numerous bug fixes
- Removed known broken connection pooling

0.10.11
-------
- Pre-build some query & filters statically, 15-30% speed up for smaller queries.
- Required field params are now positional, so Python and IDE linters will pick up on it easier.
- Filtering also applies DB-specific transforms, Fixes #62
- Fixed recursion error on m2m management with big lists

0.10.10
-------
- Refactor ``Tortoise.init()`` and test runner to not re-create connections per test, so now tests pass when using an SQLite in-memory database
- Can pass event loop to test initializer function: ``initializer(loop=loop)``
- Fix relative URI for SQLite
- Better error message for invalid filter param.
- Better error messages for missing/bad field params.
- ``nose2`` plugin
- Test utilities compatible with ``py.test``

0.10.9
------
- Uses macros on SQLite driver to minimise syncronisation. ``aiosqlite>=0.7.0``
- Uses prepared statements for insert, large insert performance increase.
- Pre-generate base pypika query object per model, providing general purpose speedup.

0.10.8
------
- Performance fixes from ``pypika>=0.15.6``
- Significant reduction in object creation time

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
* Refactored ``Tortoise.init()`` to init all connections and discover models from config passed
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
* Added support for nested queries for ``values`` and ``values_list``:

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
- Field kwarg ``default`` now accepts functions.

0.4.0
-----
- Immutable QuerySet. ``unique`` flag for fields

0.3.0
-----
* Added schema generation and more options for fields:

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
* Added filtering and ordering by related models fields:

  .. code-block:: python3

      await Tournament.filter(
          events__name__in=['1', '3']
      ).order_by('-events__participants__name').distinct()
