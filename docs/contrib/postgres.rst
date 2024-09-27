.. _contrib_postgre:

========
Postgres
========

Indexes
=======

Postgres specific indexes.

.. autoclass:: tortoise.contrib.postgres.indexes.BloomIndex
.. autoclass:: tortoise.contrib.postgres.indexes.BrinIndex
.. autoclass:: tortoise.contrib.postgres.indexes.GinIndex
.. autoclass:: tortoise.contrib.postgres.indexes.GistIndex
.. autoclass:: tortoise.contrib.postgres.indexes.HashIndex
.. autoclass:: tortoise.contrib.postgres.indexes.SpGistIndex

Fields
======

Postgres specific fields.

.. autoclass:: tortoise.contrib.postgres.fields.ArrayField
.. autoclass:: tortoise.contrib.postgres.fields.TSVectorField


Functions
=========

.. autoclass:: tortoise.contrib.postgres.functions.ToTsVector
.. autoclass:: tortoise.contrib.postgres.functions.ToTsQuery
.. autoclass:: tortoise.contrib.postgres.functions.PlainToTsQuery

Search
======

Postgres full text search.

.. autoclass:: tortoise.contrib.postgres.search.SearchCriterion
