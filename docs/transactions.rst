.. _transactions:

============
Transactions
============

Tortoise ORM provides a simple way to manage transactions. You can use the
``atomic()`` decorator or ``in_transaction()`` context manager.

``atomic()`` and ``in_transaction()`` can be nested, and the outermost block will
be the one that actually commits the transaciton. Tortoise ORM doesn't support savepoints yet.

In most cases ``asyncio.gather`` or similar ways to spin up concurrent tasks can be used safely
when querying the database or using transactions. Tortoise ORM will ensure that for the duration
of a query, the database connection is used exclusively by the task that initiated the query.


.. automodule:: tortoise.transactions
    :members:
    :undoc-members:
