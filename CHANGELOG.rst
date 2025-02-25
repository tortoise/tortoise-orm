.. _changelog:

=========
Changelog
=========

.. rst-class:: emphasize-children

0.24
====

0.24.2 (Unreleased)
------

Fixed
^^^^^
- Fix model with multi m2m fields generates wrong references name (#1897)

0.24.1
------
Added
^^^^^
- Implement __contains, __contained_by, __overlap and __len for ArrayField (#1877)

Fixed
^^^^^
- Fix update pk field raises unfriendly error (#1873)
- Using `.distinct()` with an annotation and `.order_by()` produces invalid SQL for PostgreSQL (#1886)


0.24.0
------
Fixed
^^^^^
- `_get_dialects`: support properties (#1859)
- Rename pypika to pypika_tortoise for fixing package name conflict (#1829)
- Concurrent connection pool initialization (#1825)

Changed
^^^^^^^
- Drop support for Python3.8 (#1848)
- Optimize field conversion to database format to speed up `create` and `bulk_create` (#1840)
- Improved query performance by optimizing SQL generation (#1837)

0.23.0
------
Added
^^^^^
- Implement savepoints for transactions (#1816)
- Added type validation for foreign key fields to ensure type safety. Now raises `ValidationError` when assigning foreign key values with incorrect model types (#1792)

Fixed
^^^^^
- Fixed a deadlock in three level nested transactions (#1810)
- Fix backward_relations in PydanticMeta (#1814)

0.22
====

0.22.2
------
Fixed
^^^^^
- Fix bug related to `Connector.div` in combined expressions. (#1794)
- Fix recovery in case of database downtime (#1796)

Changed
^^^^^^^
- Parametrizes UPDATE, DELETE, bulk update and create operations (#1785)
- Parametrizes related field queries (#1797)

Added
^^^^^
- CharEnumField and IntEnumField is supported by pydantic_model_creator (#1798)

0.22.1
------
Fixed
^^^^^
- Fix unable to use ManyToManyField if OneToOneField passed as Primary Key (#1783)
- Fix sorting by Term (e.g. RawSQL) (#1788)

Changed
^^^^^^^
- Parametrizes SELECT queries including `.count()`, `.exists()`, `.values()`, `.values_list()` (#1777)

0.22.0
------
Fixed
^^^^^
- Fix enums not quoted, allowing using of str enums for filters (#1776)
- Primary key field should not be nullable in pydantic schema (#1778)
- Fix ambiguous column name when grouping with joining (#1766)
- Fix same model returned by pydantic_model_creator calls with different arguments (#1741)

Added
^^^^^
- JSONField adds optional generic support, and supports OpenAPI document generation by specifying `field_type` as a pydantic BaseModel (#1763)
- Add table_name_generator attribute to Tortoise.init for dynamic table name generation (#1770)
- Support for annotation and joins F() expressions (#1761) (#1765)
- Allow use of annotate fields within Case-When expression (#1748)
- Added new queryset methods: last(), latest(), earliest() (#1754) (#1756)

Changed
^^^^^^^
- Change old pydantic docs link to new one (#1775).
- Refactored pydantic_model_creator, interface not changed  (#1745)
- Values are no longer validated to be right type upon loading from database (#1750)
- Refactored private field names in queryset classes (#1751)

0.21
====

0.21.7 <../0.21.7>`_ - 2024-10-14
------
Fixed
^^^^^
- Fix unittest error with pydantic2.9 (#1734)
- Fix bug when using annotate and count at the same time but the annotation does not match anything, leading to an IndexError (#1707)
- Added missing field_type for TimeDeltaField (#1462) (#1699)
- improve jsonfield type hint (#1700)
- Fix bug in tortoise.models.Model When a QuerySet uses the only function and then uses the print function to print the returned result, an AttributeError is generated (#1724)
- Update the pylint plugin to latest astroid version (#1708)

Added
^^^^^
- Add POSIX Regex support for PostgreSQL and MySQL (#1714)
- support app=None for tortoise.contrib.fastapi.RegisterTortoise (#1733)

0.21.6 <../0.21.6>`_ - 2024-08-17
------
Fixed
^^^^^
- Fix bug in `pydantic_model_creator` when a foreign key is not included in `include` param. (#1430)
- Fix bug in `contrib.sanic.register_tortoise` causing a deadlock when using asyncpg and > 1 workers (#1696)
- Open psycopg pool with `.open()` to remove deprecated warning (#1697)
- Fix bug in `bulk_update` when pk field is not `id` (#1698)
- Fix mysql uuid compression bug (#1687)
- Fix comment for fk fields without constraint for mysql (#1679)
- Removed no_delay option for postgres, as it wasn't doing anything (#1677)
- Fix bug in `tortoise.models.Model` When a QuerySet uses the only function and then uses the print function to print the returned result, an AttributeError is generated. (#1723)

0.21.5 <../0.21.5>`_ - 2024-07-18
------
Added
^^^^^
- Propagate `_create_db` parameter to RegisterTortoise. (#1676)

0.21.4 <../0.21.4>`_ - 2024-07-03
------
Added
^^^^^
- Add ObjectDoesNotExistError to show better 404 message. (#759)
- DoesNotExist and MultipleObjectsReturned support 'Type[Model]' argument. (#742)(#1650)
- Add argument use_tz and timezone to RegisterTortoise. (#1649)
- Support await `tortoise.contrib.fastapi.RegisterTortoise`. (#1662)
- Add `tortoise.contrib.test.init_memory_sqlite`. (#1657)

Fixed
^^^^^
- Fix `update_or_create` errors when field value changed. (#1584)
- Fix bandit check error (#1643)
- Fix potential race condition in ConnectionWrapper (#1656)
- Fix py312 warning for datetime.utcnow (#1661)
- Fix reusing values and value_list queries (#780)

Changed
^^^^^^^
- Remove obsolete loop._selector from contrib/test. (#659)(#1636)

`0.21.3 <../0.21.3>`_ - 2024-06-01
------
Fixed
^^^^^
- Fix `bulk_update` when using source_field for pk (#1633)

`0.21.2 <../0.21.2>`_ - 2024-05-25
------
Added
^^^^^
- Add `create_unique_index` argument to M2M field and default if it is true (#1620)

`0.21.1 <../0.21.1>`_ - 2024-05-24
------
Fixed
^^^^^
- Fix error on using old style `pk=True`

`0.21.0 <../0.21.0>`_ - 2024-05-23
------
Added
^^^^^
- Enhancement for FastAPI lifespan support (#1371)
- Add __eq__ method to Q to more easily test dynamically-built queries (#1506)
- Added PlainToTsQuery function for postgres (#1347)
- Allow field's default keyword to be async function (#1498)
- Add support for queryset slicing. (#1341)

Fixed
^^^^^
- Fix `DatetimeField` use '__year' report `'int' object has no attribute 'utcoffset'`. (#1575)
- Fix `bulk_update` when using custom fields. (#1564)
- Fix `optional` parameter in `pydantic_model_creator` does not work for pydantic v2. (#1551)
- Fix `get_annotations` now evaluates annotations in the default scope instead of the app namespace. (#1552)
- Fix `get_or_create` method. (#1404)
- Use `index_name` instead of `BaseSchemaGenerator._generate_index_name` to generate index name.
- Use subquery for count() and exists() in `QuerySet` to match count result to `QuerySet` result. (#1607)

Changed
^^^^^^^
- Change `utils.chunk` from function to return iterables lazily.
- Removed lower bound of id keys in generated pydantic models. (#1602)
- Rename Field initial arguments `pk`/`index` to `primary_key`/`db_index`. (#1621)
- Renamed `Model.check` method to `Model._check` to avoid naming collision issues  (#1559) (#1550)

Breaking Changes
^^^^^^^^^^^^^^^^
- `bulk_create` now does not return anything. (#1614)

0.20
====

0.20.1
------
Added
^^^^^
- Add binary compression support for `UUIDField` in `MySQL`. (#1458)
- Only `Model`, `Tortoise`, `BaseDBAsyncClient`, `__version__`, and `connections` are now exported from `tortoise`
- Add parameter `validators` to `pydantic_model_creator`. (#1471)

Fixed
^^^^^
- Fix order of fields in `ValuesListQuery` when it has more than 10 fields. (#1492)
- Fix pydantic v2 pydantic_model_creator nullable field not optional. (#1454)
- Fix pydantic v2.5 unittest error. (#1535)
- Fix pydantic_model_creator `exclude_readonly` parameter not working.
- Fix annotation propagation for non-filter queries. (#1590)
- Fix blacksheep example unittest error. (#1534)

0.20.0
------
Added
^^^^^
- Allow ForeignKeyField(on_delete=NO_ACTION) (#1393)
- Support `pydantic` 2.0. (#1433)

Fixed
^^^^^
- Fix foreign key constraint not generated on MSSQL Server. (#1400)
- Fix testcase error with python3.11 (#1308)

Breaking Changes
^^^^^^^^^^^^^^^^
- Drop support for `pydantic` 1.x.
- Drop support for `python` 3.7.
- Param `config_class` of `pydantic_model_creator` is renamed to `model_config`.
- Attr `config_class` of `PydanticMeta` is renamed to `model_config`.

0.19
====

0.19.3
------
Added
^^^^^
- Added config_class option to pydantic model genator that allows the developer to customize the generated pydantic model's `Config` class. (#1048)
Fixed
^^^^^
- Fastapi example test not working. (#1029)
- Fix create index sql error. (#1202)
- Fix dependencies resolve error. (#1246)
- Fix ignoring zero value of limit. (#1270)
- Fix ForeignKeyField is none when fk is integer 0. (#1274)
- Fix limit ignore zero. (#1270)
- Fix min/max value validators for decimal fields. (#1291)

0.19.2
------
Added
^^^^^
- Added `schema` attribute to Model's Meta to specify exact schema to use with the model.
Fixed
^^^^^
- Mixin does not work. (#1133)
- `using_db` wrong position in model shortcut methods. (#1150)
- Fixed connection to `Oracle` database by adding database info to DBQ in connection string.
- Fixed ORA-01435 error while using `Oracle` database (#1155)
- Fixed processing of `ssl` option in MySQL connection string.
- Fixed type hinting for `QuerySetSingle`.

0.19.1
------
Added
^^^^^
- Added `Postgres`/`SQLite` partial indexes support. (#1103)
- Added `Microsoft SQL Server`/`Oracle` support, powered by `asyncodbc <https://github.com/tortoise/asyncodbc>`_, note that which is **not fully tested**.
- Added `optional` parameter to `pydantic_model_creator`. (#770)
- Added `using_db` parameter to `Model` shortcut methods. (#1109)
Fixed
^^^^^
- `TimeField` for `MySQL` will return `datetime.timedelta` object instead of `datetime.time` object.
- Fix on conflict do nothing. (#1122)
- Fix `_custom_generated_pk` attribute not set in `Model._init_from_db` method. (#633)

0.19.0
------
Added
^^^^^
- Added psycopg backend support.
- Added a new unified and robust connection management interface to access DB connections which includes support for
  lazy connection creation and much more. For more details, check out this `PR <https://github.com/tortoise/tortoise-orm/pull/1001>`_
- Added `TimeField`. (#1054)
- Added `ArrayField`.
Fixed
^^^^^
- Fix `bulk_create` doesn't work correctly with more than 1 update_fields. (#1046)
- Fix `bulk_update` errors when setting null for a smallint column on postgres. (#1086)
Deprecated
^^^^^^^^^^
- Existing connection management interface and related public APIs which are deprecated:
 - `Tortoise.get_connection`
 - `Tortoise.close_connections`
Changed
^^^^^^^
- Refactored `tortoise.transactions.get_connection` method to `tortoise.transactions._get_connection`.
 Note that this method has now been marked **private to this module and is not part of the public API**

0.18.1
------
Added
^^^^^
- Add on conflict do update for bulk_create. (#1024)
Fixed
^^^^^
- Fix `bulk_create` error. (#1012)
- Fix unittest invalid.
- Fix `bulk_update` in `postgres` with some type. (#968) (#1022)

0.18.0
------
Added
^^^^^
- Add Case-When support. (#943)
- Add `Rand`/`Random` function in contrib. (#944)
- Add `ON CONFLICT` support in `INSERT` statements. (#428)
Fixed
^^^^^
- Fix `bulk_update` error when pk is uuid. (#986)
- Fix mutable default value. (#969)
Changed
^^^^^^^
- Move `Function`, `Aggregate` from `functions.py` to `expressions.py`. (#943)
- Move `Q` from `query_utils.py` to `expressions.py`.
- Replace `python-rapidjson` to `orjson`.
Removed
^^^^^^^
- Remove `asynctest` and use `unittest.IsolatedAsyncioTestCase`. (#416)
- Remove `py37` support in tests.
- Remove `green` and `nose2` test runner.

0.17
====
0.17.8
------
Added
^^^^^
- Add `Model.raw` method to support the raw sql query.
- Add `QuerySet.bulk_update` method. (#924)
- Add `QuerySet.in_bulk` method.
- Add `MaxValueValidator` and `MinValueValidator` (#927)
Fixed
^^^^^
- Fix `QuerySet` subclass being lost when `_clone` is run on the instance.
- Fix bug in `.values` with `source_field`. (#844)
- Fix `contrib.blacksheep` exception handlers, use builtin json response. (#914)
- Fix Indexes defined in Meta class do not make use of `exists` parameter in their template (#928)
Changed
^^^^^^^
- Allow negative values with `IntEnumField`. (#889)
- Make `.values()` and `.values_list()` awaited return more consistent. (#899)

0.17.7
------
- Fix `select_related` behaviour for forward relation. (#825)
- Fix bug in nested `QuerySet` and `Manager`. (#864)
- Add `Concat` function for MySQL/PostgreSQL. (#873)
- Patch for use_index/force_index mutable problem when making query. (#888)
- Lift annotation field's priority in make query. (#883)
- Make use/force index available in select type Query. (#893)
- Fix all logging to use Tortoise's logger instead of root logger. (#879)
- Rename `db_client` logger to `tortoise.db_client`.
- Add `indexes` to `Model.describe`.

0.17.6
------
- Add `RawSQL` expression.
- Fix columns count with annotations in `_make_query`. (#776)
- Make functions nested. (#828)
- Add `db_constraint` in field describe.

0.17.5
------
- Set `field_type` of fk and o2o same to which relation field type. (#443)
- Fix error sql for `.sql()` call more than once. (#796)
- Fix incorrect splitting of the import route when using Router (#798)
- Fix `filter` error after `annotate` with `F`. (#806)
- Fix `select_related` for reverse relation. (#808)

0.17.4
------
- Fix `update_or_create`. (#782)
- Add `contains`, `contained_by` and `filter` to `JSONField`

0.17.3
------
- Fix duplicates when using custom through association class on M2M relations
- Fix `update_or_create` and `get_or_create`. (#721)
- Fix `refresh_from_db` without fields pass. (#734)
- Make `update` query work with `limit` and `order_by`. (#748)
- Add `Subquery` expression. (#756) (#9) (#337)
- Use JSON in JSONField.

0.17.2
------
- Add more `index` types.
- Add `force_index`, `use_index` to `queryset`.
- Fix `F` in update error with `update_fields`.
- Make `delete` query work with `limit` and `order_by`. (#697)
- Filter backward FK fields with `IS NULL` and `NOT IS NULL` filters (#700)
- Add `select_for_update` in `update_or_create`. (#702)
- Add `Model.select_for_update`.
- Add `__search` full text search to queryset.

0.17.1
------
- Fix type for modules.
- Fix `select_related` when related model specified more than once. (#679)
- Add `__iter__` to model, now can just return model/models in `fastapi` response.
- Fix `in_transaction` bug caused by 'router'. (#677) (#678)

0.17.0
-------
- Add date part extract filtering.
- Add `Manager` support.
- Add db router support.
- Add `nowait`, `skip_locked`, `of` parameters to `queryset.select_for_update`.
- Add field name to validation exceptions.
- Compatible with `asyncmy <https://github.com/long2ice/asyncmy>`_.
- Replace pypika to `pypika-tortoise <https://github.com/tortoise/pypika-tortoise>`_.

0.16
====
0.16.21
-------
- Fixed validating JSON before decoding. (#623)
- Add model method `update_or_create`.
- Add `batch_size` parameter for `bulk_create` method.
- Fix save with F expression and field with source_field.

0.16.20
-------
- Add model field validators.
- Allow function results in group by. (#608)

0.16.19
-------
- Replace set `TZ` environment variable to `TIMEZONE` to avoid affecting global timezone.
- Allow passing module objects to `models_paths` param of `Tortoise.init_models()`. (#561)
- Implement `PydanticMeta.backward_relations`. (#536)
- Allow overriding `PydanticMeta` in `PydanticModelCreator`. (#536)
- Fixed make_native typo to make_naive in timezone module

0.16.18
-------
- Support custom function in update. (#537)
- Add `Model.refresh_from_db`. (#549)
- Add timezone support, **be careful to upgrade to this version**, see `docs <https://tortoise-orm.readthedocs.io/en/latest/timezone.html>`_ for details. (#335)
- Remove `aerich` in case of cyclic dependency. (#558)

0.16.17
-------
- Add `on_delete` in `ManyToManyField`. (#508)
- Support `F` expression in `annotate`. (#475)
- Fix `QuerySet.select_related` in case of join same table twice. (#525)
- Integrate Aerich into the install. (#530)

0.16.16
-------
- Fixed inconsistency in integrity error exception of FastAPI
- add OSError to _get_comments except block

0.16.15
-------
- Make `DateField` accept valid date str.
- Add `QuerySet.select_for_update()`.
- check ``default`` for not ``None`` on pydantic model creation
- propagate default to pydantic model
- Add `QuerySet.select_related()`.
- Add custom attribute name for Prefetch instruction.
- Add `db_constraint` for `RelationalField` family.

0.16.14
-------
- Make ``F`` expression work with ``QuerySet.filter()``.
- Include ``py.typed`` in source distribution.
- Added ``datetime`` parsing from ``int`` for ``fields.DatetimeField``.
- ``get_or_create`` passes the ``using_db=`` on if provided.
- Allow custom ``loop`` and ``connection_class`` parameters to be passed on to asyncpg.

0.16.13
-------
- Default install of ``tortoise-orm`` now installs with no C-dependencies, if you want to use the C accelerators, please do a ``pip install tortoise-orm[accel]`` instead.
- Added ``<instance>.clone()`` method that will create a cloned instance in memory. To persist it you still need to call ``.save()``
- ``.clone()`` will raise a ``ParamsError`` if tortoise can't generate a primary key. In that case do a ``.clone(pk=<newval>)``
- If manually setting the primary key value to ``None`` and the primary key can be automatically generated, this will create a new record. We however still recommend the ``.clone()`` method instead.
- ``.save()`` can be forced to do a create by setting ``force_create=True``
- ``.save()`` can be forced to do an update by setting ``force_update=True``
- Setting ``update_fields`` for a ``.save()`` operation will strongly prefer to do an update if possible

0.16.12
-------
- Make ``Field.default`` effect on db level when generate table
- Add converters instead of importing from pymysql
- Fix postgres BooleanField default value convent
- Fix ``JSONField`` typed in ``pydantic_model_creator``
- Add ``.sql()`` method on ``QuerySet``

0.16.11
-------
- fix: ``sqlite://:memory:`` in Windows thrown ``OSError: [WinError 123]``
- Support ``bulk_create()`` insertion of records with overridden primary key when the primary key is DB-generated
- Add ``queryset.exists()`` and ``Model.exists()``.
- Add model subscription lookup, ``Model[<pkval>]`` that will return the object or raise ``KeyError``

0.16.10
-------
- Fix bad import of ``basestring``
- Better handling of NULL characters in strings. Fixes SQLite, raises better error for PostgreSQL.
- Support ``.group_by()`` with join now

0.16.9
------
- Support ``F`` expression in ``.save()`` now
- ``IntEnumField`` accept valid int value and ``CharEnumField`` accept valid str value
- Pydantic models get created with globally unique identifier
- Leaf-detection to minimize duplicate Pydantic model creation
- Pydantic models with a Primary Key that is also a raw field of a relation is now not hidden when ``exclude_raw_fields=True`` as it is a critically important field
- Raise an informative error when a field is set as nullable and primary key at the same time
- Foreign key id's are now described to have the positive-integer range of the field it is related to
- Fixed prefetching over OneToOne relations
- Fixed ``__contains`` for non-text fields (e.g. ``JSONB``)

0.16.8
------
- Allow ``Q`` expression to function with ``_filter`` parameter on aggregations
- Add manual ``.group_by()`` support
- Fixed regression where ``GROUP BY`` class is missing for an aggregate with a specified order.

0.16.7
------
- Added preliminary support for Python 3.9
- ``TruncationTestCase`` now properly quotes table names when it clears them out.
- Add model signals support
- Added ``app_label`` to ``test initializer(...)`` and ``TORTOISE_TEST_APP`` as test environment variable.

0.16.6
------
.. warning::

    This is a security fix release. We recommend everyone update.

Security fixes
^^^^^^^^^^^^^^

- Fixed SQL injection issue in MySQL
- Fixed SQL injection issues in MySQL when using ``contains``, ``starts_with`` or ``ends_with`` filters (and their case-insensitive counterparts)
- Fixed malformed SQL for PostgreSQL and SQLite when using ``contains``, ``starts_with`` or ``ends_with`` filters (and their case-insensitive counterparts)

Other changes
^^^^^^^^^^^^^

* Added support for partial models:

  To create a partial model, one can do a ``.only(<fieldnames-as-strings>)`` as part of the QuerySet.
  This will create model instances that only have those values fetched.

  Persisting changes on the model is allowed only when:

  * All the fields you want to update is specified in ``<model>.save(update_fields=[...])``
  * You included the Model primary key in the ``.only(...)``

  To protect against common mistakes we ensure that errors get raised:

  * If you access a field that is not specified, you will get an ``AttributeError``.
  * If you do a ``<model>.save()`` a ``IncompleteInstanceError`` will be raised as the model is, as requested, incomplete.
  * If you do a ``<model>.save(update_fields=[...])`` and you didn't include the primary key in the ``.only(...)``,
    then ``IncompleteInstanceError`` will be raised indicating that updates can't be done without the primary key being known.
  * If you do a ``<model>.save(update_fields=[...])`` and one of the fields in ``update_fields`` was not in the ``.only(...)``,
    then ``IncompleteInstanceError`` as that field is not available to be updated.

- Fixed bad SQL generation when doing a ``.values()`` query over a Foreign Key
- Added `<model>.update_from_dict({...})` that will mass update values safely from a dictionary
- Fixed processing URL encoded password in connection string

0.16.5
------
* Moved ``Tortoise.describe_model(<MODEL>, ...)`` to ``<MODEL>.describe(...)``
* Deprecated ``Tortoise.describe_model()``
* Fix for ``generate_schemas`` param being ignored in ``tortoise.contrib.quart.register_tortoise``
* Fix join query with `source_field` param

0.16.4
------
* More consistent escaping of db columns, fixes using SQL reserved keywords as field names with a function.
* Fix the aggregates using the wrong side of the join when doing a self-referential aggregation.
* Fix ``F`` functions wrapped forgetting about ``distinct=True``

0.16.3
------
* Fixed invalid ``var IN ()`` SQL generated using ``__in=`` and ``__not_in`` filters.
* Fix bug with order_by on nested fields
* Fix joining with self by reverse-foreign-key for filtering and annotation

0.16.2
------
* Default ``values()`` & ``values_list()`` now includes annotations.
* Annotations over joins now work correctly with ``values()`` & ``values_list()``
* Ensure ``GROUP BY`` precedes ``HAVING`` to ensure that filtering by aggregates work correctly.
* Fix bug with join query with aggregation
* Cast ``BooleanField`` values correctly on SQLite & MySQL

0.16.1
------
* ``QuerySetSingle`` now has better code completion
* Created Pydantic models will now have the basic validation elements:

  * ``required`` is correctly populated for required fields
  * ``nullable`` is added to the schema where nulls are accepted
  * ``maxLength`` for CharFields
  * ``minimum`` & ``maximum`` values for integer fields

  To get Pydantic to handle nullable/default fields correctly one should do a ``**user.dict(exclude_unset=True)`` when passing values to a Model class.

* Added ``FastAPI`` helper that is based on the ``starlette`` helper but optionally adds helpers to catch and report with proper error ``DoesNotExist`` and ``IntegrityError`` Tortoise exceptions.
* Allows a Pydantic model to exclude all read-only fields by setting ``exclude_readonly=True`` when calling ``pydantic_model_creator``.
* a Tortoise ``PydanticModel`` now provides two extra helper functions:

  * ``from_queryset``: Returns a ``List[PydanticModel]`` which is the format that e.g. FastAPI expects
  * ``from_queryset_single``: allows one to avoid calling ``await`` multiple times to get the object and all its related items.


0.16.0
------
.. caution::
   **This release drops support for Python 3.6:**

   Tortoise ORM now requires a minimum of CPython 3.7

New features:
^^^^^^^^^^^^^
* Model docstrings and ``#:`` comments directly preceding Field definitions are now used as docstrings and DDL descriptions.

  This is now cleaned and carried as part of the ``docstring`` parameter in ``describe_model(...)``

  If one doesn't explicitly specify a Field ``description=`` or Model ``Meta.table_description=`` then we default to the first line as the description.
  This is done because a description is submitted to the DB, and needs to be short (depending on DB, 63 chars) in size.

  Usage example:

  .. code-block:: python3

    class Something(Model):
        """
        A Docstring.

        Some extra info.
        """

        # A regular comment
        name = fields.CharField(max_length=50)
        #: A docstring comment
        chars = fields.CharField(max_length=50, description="Some chars")
        #: A docstring comment
        #: Some more detail
        blip = fields.CharField(max_length=50)

    # When looking at the describe model:
    {
        "description": "A Docstring.",
        "docstring": "A Docstring.\n\nSome extra info.",
        ...
        "data_fields": [
            {
                "name": "name",
                ...
                "description": null,
                "docstring": null
            },
            {
                "name": "chars",
                ...
                "description": "Some chars",
                "docstring": "A docstring comment"
            },
            {
                "name": "blip",
                ...
                "description": "A docstring comment",
                "docstring": "A docstring comment\nSome more detail"
            }
        ]
    }

* Early Partial Init of models.

  We now have an early init of models, which can be useful when needing Models that are not bound to a DB, but otherwise complete.
  e.g. Schema generation without needing to be properly set up.

  Usage example:

  .. code-block:: python3

    # Lets say you defined your models in "some/models.py", and "other/ddef.py"
    # And you are going to use them in the "model" namespace:
    Tortoise.init_models(["some.models", "other.ddef"], "models")

    # Now the models will have relationships built, so introspection of schema will be comprehensive

* Pydantic serialisation.

  We now include native support for automatically building a Pydantic model from Tortoise ORM models.
  This will correctly model:

  * Data Fields
  * Relationships (FK/O2O/M2M)
  * Callables

  At this stage we only support serialisation, not deserialisation.

  For mode information, please see :ref:`contrib_pydantic`

- Allow usage of ``F`` expressions to in annotations. (#301)
- Now negative number with ``limit(...)`` and ``offset(...)`` raise ``ParamsError``. (#306)
- Allow usage of Function to ``queryset.update()``. (#308)
- Add ability to supply ``distinct`` flag to Aggregate (#312)


Bugfixes:
^^^^^^^^^
- Fix default type of ``JSONField``

Removals:
^^^^^^^^^
- Removed ``tortoise.aggregation`` as this was deprecated since 0.14.0
- Removed ``start_transaction`` as it has been broken since 0.15.0
- Removed support for Python 3.6 / PyPy-3.6, as it has been broken since 0.15.0

  If you still need Python 3.6 support, you can install ``tortoise-orm<0.16`` as we will still backport critical bugfixes to the 0.15 branch for a while.

.. rst-class:: emphasize-children

0.15
====

0.15.24
-------
- Fixed regression where ``GROUP BY`` class is missing for an aggregate with a specified order.

0.15.23
-------
- Fixed SQL injection issue in MySQL
- Fixed SQL injection issues in MySQL when using ``contains``, ``starts_with`` or ``ends_with`` filters (and their case-insensitive counterparts)
- Fixed malformed SQL for PostgreSQL and SQLite when using ``contains``, ``starts_with`` or ``ends_with`` filters (and their case-insensitive counterparts)

0.15.22
-------
* Fix the aggregates using the wrong side of the join when doing a self-referential aggregation.
* Fix for ``generate_schemas`` param being ignored in ``tortoise.contrib.quart.register_tortoise``

0.15.21
-------
* Fixed invalid ``var IN ()`` SQL generated using ``__in=`` and ``__not_in`` filters.
* Fix bug with order_by on nested fields
* Fix joining with self by reverse-foreign-key for filtering and annotation

0.15.20
-------
* Default ``values()`` & ``values_list()`` now includes annotations.
* Annotations over joins now work correctly with ``values()`` & ``values_list()``
* Ensure ``GROUP BY`` precedes ``HAVING`` to ensure that filtering by aggregates work correctly.
* Cast ``BooleanField`` values correctly on SQLite & MySQL

0.15.19
-------
- Fix Function with ``source_field`` option. (#311)

0.15.18
-------
- Install on Windows does not require a C compiler any more.
- Fix ``IntegrityError`` with unique field and ``get_or_create``

0.15.17
-------
- Now ``get_or_none(...)``, classmethod of ``Model`` class, works in the same way as ``queryset``

0.15.16
-------
- ``get_or_none(...)`` now raises ``MultipleObjectsReturned`` if multiple object fetched. (#298)

0.15.15
-------
- Add ability to suppply a ``to_field=`` parameter for FK/O2O to a non-PK but still uniquely indexed remote field. (#287)

0.15.14
-------
- add F expression support in ``queryset.update()`` - This allows for atomic updates of data in the database. (#294)

0.15.13
-------
- Applies default ordering on related queries
- Fix post-ManyToMany related queries not being evaluated correctly
- Ordering is now preserved on ManyToMany related fetches
- Fix aggregate function on joined table to use correct primary key
- Fix filtering by backwards FK to use correct primary key

0.15.12
-------
- Added ``range`` filter to support ``between and`` syntax

0.15.11
-------
- Added ``ordering`` option for model ``Meta`` class to apply default ordering

0.15.10
-------
- Bumped requirements to cater for newer feature use (#282)

0.15.9
------
- Alias Foreign Key joins as we can have both self-referencing and duplicate joins to the same table.
  This generates SQL that differentiates between which instance of the table to work with.

0.15.8
------
- ``TextField`` now recommends usage of ``CharField`` if wanting unique indexing instead of just saying "indexing not supported"
- ``.count()`` now honours offset and limit
- Testing un-awaited ``ForeignKeyField`` as a boolean expression will automatically resolve as ``False`` if it is None
- Awaiting a nullable ``ForeignKeyField`` won't touch the DB if it is ``None``

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
  We can't guarantee that it will be properly indexed or unique in all cases.
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
- Enable foreign key enforcement on SQLite for builds where it was optional.

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


.. rst-class:: emphasize-children

0.14
====

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
- One can now specify compound indexes in the ``Meta:`` class using ``indexes``. It works just like ``unique_together``.

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

.. rst-class:: emphasize-children

0.13
====

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


.. rst-class:: emphasize-children

0.12
====

0.12.7 (retracted)
------------------
- Support connecting to PostgreSQL via Unix domain socket (simple case).
- Self-referential Foreign and Many-to-Many keys are now allowed

0.12.6 / 0.12.8
---------------
* Handle a ``__models__`` variable within modules to override the model discovery mechanism.

    If you define the ``__models__`` variable in ``yourapp.models`` (or wherever you specify to load your models from),
    ``generate_schema()`` will use that list, rather than automatically finding all models for you.

- Split model constructor into from-Python and from-DB paths, leading to 15-25% speedup for large fetch operations.
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

  That primary key will be accessible through a reserved field ``pk`` which will be an alias of whichever field has been nominated as a primary key.
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


.. rst-class:: emphasize-children

0.11
====

0.11.13
-------
- Fixed connection retry to work with transactions
- Added broader PostgreSQL connection failure detection

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

.. rst-class:: emphasize-children

0.10
====

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
- Set single_connection to True by default, as there is known issues with connection pooling
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


.. rst-class:: emphasize-children

0.9 & older
===========

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
