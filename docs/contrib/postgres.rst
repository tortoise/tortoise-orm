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

Full text search uses ``TSVECTOR`` data and PostgreSQL search functions. Tortoise provides
field support, expression helpers, and ranking/headline utilities similar to Django.

Generated TSVECTOR columns require PostgreSQL 12+.

.. code-block:: python3

    from tortoise import fields, models
    from tortoise.contrib.postgres.fields import TSVectorField
    from tortoise.contrib.postgres.search import SearchQuery, SearchRank, SearchVector

    class Article(models.Model):
        title = fields.CharField(max_length=200)
        body = fields.TextField()
        search = TSVectorField(
            source_fields=("title", "body"),
            config="english",
            weights=("A", "B"),
            stored=True,
        )

    query = SearchQuery("postgres", search_type="websearch", config="english")
    vector = SearchVector("title", "body", config="english")
    rank = SearchRank(vector, query, normalization=32)
    results = (
        await Article.annotate(rank=rank)
        .filter(search__search=query)
        .order_by("-rank")
    )

.. code-block:: python3

    from tortoise.contrib.postgres.search import SearchHeadline

    results = await Article.annotate(
        snippet=SearchHeadline("body", query, start_sel="<b>", stop_sel="</b>")
    )

.. autoclass:: tortoise.contrib.postgres.search.SearchVector
.. autoclass:: tortoise.contrib.postgres.search.SearchQuery
.. autoclass:: tortoise.contrib.postgres.search.SearchRank
.. autoclass:: tortoise.contrib.postgres.search.SearchHeadline
.. autoclass:: tortoise.contrib.postgres.search.Lexeme
.. autoclass:: tortoise.contrib.postgres.search.SearchCriterion
