.. _expressions:

===========
Expressions
===========

Q Expression
============

The ``Q`` Expression provides advanced querying capabilities beyond the basic filtering provided by ``<model>.filter()``. Q objects enable complex query construction and can be used as arguments to ``<model>.filter()``.

Key features of ``Q`` objects include:
 - Construction of OR conditions
 - Creation of nested filters
 - Filter inversion
 - Combination of multiple conditions into complex queries

``Q`` objects accept any filtering parameters that ``<model>.filter()`` supports. Please refer to :ref:`query_api` for a complete list of available options.

``Q`` objects can be combined using bitwise operators:
 - ``|`` for OR operations
 - ``&`` for AND operations

Example of using Q objects to query events with specific names:

.. code-block:: python3

    found_events = await Event.filter(
        Q(name='Event 1') | Q(name='Event 2')
    )

Q objects also support nesting. The following example is equivalent to the previous one:

.. code-block:: python3

    found_events = await Event.filter(
        Q(Q(name='Event 1'), Q(name='Event 2'), join_type="OR")
    )

If the join_type parameter is not specified, it defaults to "AND".

.. note::
    Q objects without filter arguments are treated as no-operation (NOP) and are excluded from the final query, regardless of whether they are used in AND or OR operations.

The NOT operation can be achieved using the negation operator (``~``):

.. code-block:: python3

    not_third_events = await Event.filter(~Q(name='3'))

.. automodule:: tortoise.expressions
    :members: Q
    :undoc-members:

F Expression
============

The ``F`` Expression represents a model field value and enables database operations on field values without loading them into Python memory. This is particularly useful for atomic operations.

Example of using F expressions for balance updates (this is just an example and such updates are not recommended for use in financial applications):

.. code-block:: python3

    from tortoise.expressions import F

    await User.filter(id=1).update(balance = F('balance') - 10)

    await User.filter(id=1).update(balance = F('balance') + F('award'), award = 0)

    # Using F expressions with .save()
    user = await User.get(id=1)
    user.balance = F('balance') - 10
    await user.save(update_fields=['balance'])

When working with F expressions, you must refresh the model instance to access updated field values:

.. code-block:: python3

    # Incorrect - balance value may be stale
    balance = user.balance

    # Correct - refresh the balance field first
    await user.refresh_from_db(fields=['balance'])
    balance = user.balance

F expressions can also be used in annotations:

.. code-block:: python3

    data = await User.annotate(idp=F("id") + 1).values_list("id", "idp")

Subquery
========

Subquery expressions can be utilized in both ``filter()`` and ``annotate()`` operations:

.. code-block:: python3

    from tortoise.expressions import Subquery

    await Tournament.annotate(ids=Subquery(Tournament.all().limit(1).values("id"))).values("ids", "id")
    await Tournament.filter(pk=Subquery(Tournament.filter(pk=t1.pk).values("id"))).first()

RawSQL
======

RawSQL provides the capability to execute raw SQL queries within ``filter()`` and ``annotate()`` operations. This offers maximum flexibility when needed:

.. code-block:: python3

    await Tournament.filter(pk=1).annotate(count=RawSQL('count(*)')).values("count")
    await Tournament.filter(pk=1).annotate(idp=RawSQL('id + 1')).filter(idp=2).values("idp")
    await Tournament.filter(pk=RawSQL("id + 1"))

Case-When Expression
====================

The Case-When expression enables the construction of conditional logic using ``CASE WHEN ... THEN ... ELSE ... END`` SQL statements.

.. autoclass:: tortoise.expressions.When

.. autoclass:: tortoise.expressions.Case

Example usage:

.. code-block:: python3

    results = await IntModel.all().annotate(
        category=Case(
            When(intnum__gte=8, then='big'),
            When(intnum__lte=2, then='small'),
            default='middle'
        )
    )
