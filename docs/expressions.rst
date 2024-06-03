.. _expressions:

===========
Expressions
===========

Q Expression
============

Sometimes you need to do more complicated queries than the simple AND ``<model>.filter()`` provides. Luckily we have Q objects to spice things up and help you find what you need. These Q-objects can then be used as argument to ``<model>.filter()`` instead.

Q objects are extremely versatile, some example use cases:
 - creating an OR filter
 - nested filters
 - inverted filters
 - combining any of the above to simply write complicated multilayer filters

Q objects can take any (special) kwargs for filtering that ``<model>.filter()`` accepts, see those docs for a full list of filter options in that regard.

They can also be combined by using bitwise operators (``|`` is OR and ``&`` is AND for those unfamiliar with bitwise operators)

For example to find the events with as name ``Event 1`` or ``Event 2``:

.. code-block:: python3

    found_events = await Event.filter(
        Q(name='Event 1') | Q(name='Event 2')
    )

Q objects can be nested as well, the above for example is equivalent to:

.. code-block:: python3

    found_events = await Event.filter(
        Q(Q(name='Event 1'), Q(name='Event 2'), join_type="OR")
    )

If join type is omitted it defaults to ``AND``.

.. note::
    Q objects without filter arguments are considered NOP and will be ignored for the final query (regardless on if they are used as ``AND`` or ``OR`` param)


Also, Q objects support negated to generate ``NOT`` (``~`` operator) clause in your query

.. code-block:: python3

    not_third_events = await Event.filter(~Q(name='3'))

.. automodule:: tortoise.expressions
    :members: Q
    :undoc-members:

F Expression
============

An `F` object represents the value of a model field. It makes it possible to refer to model field values and perform database operations using them without actually having to pull them out of the database into Python memory.

For example to use ``F`` to update user balance atomic:

.. code-block:: python3

    from tortoise.expressions import F

    await User.filter(id=1).update(balance = F('balance') - 10)
    await User.filter(id=1).update(balance = F('balance') + F('award'), award = 0)

    # or use .save()
    user = await User.get(id=1)
    user.balance = F('balance') - 10
    await user.save(update_fields=['balance'])

For this if you want access updated `F` field again, you should call `refresh_from_db` to refresh special fields first.

.. code-block:: python3

    # Can't do this!
    balance = user.balance
    await user.refresh_from_db(fields=['balance'])
    # Great!
    balance = user.balance

And you can also use `F` in `annotate`.

.. code-block:: python3

    data = await User.annotate(idp=F("id") + 1).values_list("id", "idp")

Subquery
========

You can use `Subquery` in `filter()` and `annotate()`.

.. code-block:: python3

    from tortoise.expressions import Subquery

    await Tournament.annotate(ids=Subquery(Tournament.all().limit(1).values("id"))).values("ids", "id")
    await Tournament.filter(pk=Subquery(Tournament.filter(pk=t1.pk).values("id"))).first()

RawSQL
======

`RawSQL` just like `Subquery` but provides the ability to write raw sql.

You can use `RawSQL` in `filter()` and `annotate()`.

.. code-block:: python3

    await Tournament.filter(pk=1).annotate(count=RawSQL('count(*)')).values("count")
    await Tournament.filter(pk=1).annotate(idp=RawSQL('id + 1')).filter(idp=2).values("idp")
    await Tournament.filter(pk=RawSQL("id + 1"))


Case-When Expression
====================

Build classic `CASE WHEN ... THEN ... ELSE ... END` sql snippet.

.. autoclass:: tortoise.expressions.When

.. autoclass:: tortoise.expressions.Case

.. code-block:: py3

    results = await IntModel.all().annotate(category=Case(When(intnum__gte=8, then='big'), When(intnum__lte=2, then='small'), default='middle'))
