.. _functions:

======================
Functions & Aggregates
======================

To apply functions to values and get aggregates computed on the DB side, one needs to annotate the QuerySet.

.. code-block:: py3

    results = await SomeModel.filter(...).annotate(clean_desc=Coalesce("desc", "N/A"))

This will add a new attribute on each ``SomeModel`` instance called ``clean_desc`` that will now contain the annotated data.

One can also call ``.values()`` or ``.values_list()`` on it to get the data as per regular.

Functions
=========

Functions apply a transform on each instance of a Field.

.. autoclass:: tortoise.functions.Trim

.. autoclass:: tortoise.functions.Length

.. autoclass:: tortoise.functions.Coalesce

.. autoclass:: tortoise.functions.Lower

.. autoclass:: tortoise.functions.Upper

.. autoclass:: tortoise.functions.Concat

.. autoclass:: tortoise.contrib.mysql.functions.Rand

.. autoclass:: tortoise.contrib.postgres.functions.Random

.. autoclass:: tortoise.contrib.sqlite.functions.Random

Aggregates
==========

Aggregated apply on the entire column, and will often be used with grouping.
So often makes sense with a ``.first()`` QuerySet.

.. autoclass:: tortoise.functions.Count

.. autoclass:: tortoise.functions.Sum

.. autoclass:: tortoise.functions.Max

.. autoclass:: tortoise.functions.Min

.. autoclass:: tortoise.functions.Avg


Base function class
===================

.. automodule:: tortoise.functions
    :members: Aggregate

    .. autoclass:: Function
        :members:

Custom functions
================
You can define custom functions which are not builtin, such as ``TruncMonth`` and ``JsonExtract`` etc.

.. code-block:: python3

    from pypika_tortoise import CustomFunction
    from tortoise.expressions import F, Function

    class TruncMonth(Function):
        database_func = CustomFunction("DATE_FORMAT", ["name", "dt_format"])

    sql = Task.all().annotate(date=TruncMonth('created_at', '%Y-%m-%d')).values('date').sql()
    print(sql)
    # SELECT DATE_FORMAT(`created_at`,'%Y-%m-%d') `date` FROM `task`

And you can also use functions in update, the example is only suitable for MySQL and SQLite, but PostgreSQL is the same.

.. code-block:: python3

    from tortoise.expressions import F
    from tortoise.functions import Function
    from pypika_tortoise.terms import Function as PupikaFunction

    class JsonSet(Function):
        class PypikaJsonSet(PupikaFunction):
            def __init__(self, field: F, expression: str, value: Any):
                super().__init__("JSON_SET", field, expression, value)

        database_func = PypikaJsonSet

    json = await JSONFields.create(data_default={"a": 1})
    json.data_default = JsonSet(F("data_default"), "$.a", 2)
    await json.save()

    # or use queryset.update()
    sql = JSONFields.filter(pk=json.pk).update(data_default=JsonSet(F("data_default"), "$.a", 3)).sql()
    print(sql)
    # UPDATE jsonfields SET data_default=JSON_SET(`data_default`,'$.a',3) where id=1
