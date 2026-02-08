Direct PyPika Queries
=====================

Tortoise exposes a public API for building and executing PyPika queries directly, without
creating model instances.

Table Access
------------

Use ``Model.get_table()`` to get a fresh PyPika ``Table``:

.. code-block:: python3

   from tortoise.models import Model
   from tortoise import fields

   class Tournament(Model):
       id = fields.IntField(pk=True)
       name = fields.TextField()

   table = Tournament.get_table()

Query Execution
---------------

Use ``execute_pypika`` to run a PyPika query and get a ``QueryResult`` with rows as dicts.

.. code-block:: python3

   from pypika_tortoise import Query
   from tortoise.query_api import execute_pypika

   table = Tournament.get_table()
   query = Query.from_(table).select(table.id, table.name).where(table.name == "Champions")

   result = await execute_pypika(query)
   print(result.rows)
   print(result.rows_affected)

If your application has multiple database connections configured, you must pass
``using_db`` explicitly:

.. code-block:: python3

   from tortoise.connection import get_connection

   db = get_connection("analytics")
   result = await execute_pypika(query, using_db=db)

Rows Affected Semantics
-----------------------

``QueryResult.rows_affected`` is always populated, but the meaning depends on backend and
query type:

* SQLite: for SELECT, it is the number of rows fetched; for UPDATE/DELETE, it is the delta
  of total changes.
* asyncpg: for SELECT, it is the number of rows fetched; for UPDATE/DELETE, it is parsed
  from the command status.
* MySQL/ODBC/psycopg: typically uses ``cursor.rowcount`` (driver-defined for some statements).

Typed Results
-------------

You can provide an optional schema to validate or type the results.

Pydantic v2 BaseModel:

.. code-block:: python3

   from pydantic import BaseModel

   class Row(BaseModel):
       id: int
       name: str

   result = await execute_pypika(query, schema=Row)
   row = result.rows[0]
   print(row.id, row.name)

Pydantic v2 TypeAdapter:

.. code-block:: python3

   from pydantic import TypeAdapter

   adapter = TypeAdapter(dict[str, int | str])
   result = await execute_pypika(query, schema=adapter)

TypedDict (typing only, no runtime validation):

.. code-block:: python3

   from typing import TypedDict

   class RowDict(TypedDict):
       id: int
       name: str

   result = await execute_pypika(query, schema=RowDict)

Parameter Binding
-----------------

PyPika will parameterize literal values for you, so avoid formatting SQL by hand:

.. code-block:: python3

   table = Tournament.get_table()
   query = Query.from_(table).select(table.id).where(table.name == "Champions")
   result = await execute_pypika(query)
   # SQL: SELECT "id" FROM "tournament" WHERE "name"=?
   # Params: ["Champions"]
