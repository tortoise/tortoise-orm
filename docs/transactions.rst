.. _transactions:

============
Transactions
============

Tortoise ORM provides a simple way to manage transactions. You can use the
``atomic()`` decorator or ``in_transaction()`` context manager.

``atomic()`` and ``in_transaction()`` can be nested. The inner blocks will create transaction savepoints,
and if an exception is raised and then caught outside of a nested block, the transaction will be rolled back
to the state before the block was entered. The outermost block will be the one that actually commits the transaction.
The savepoints are supported for Postgres, MySQL, MSSQL and SQLite. For other databases, it is advised to
propagate the exception to the outermost block to ensure that the transaction is rolled back.

  .. code-block:: python3

    # this block will commit changes on exit
    async with in_transaction():
        await MyModel.create(name='foo')
        try:
            # this block will create a savepoint and rollback to it if an exception is raised
            async with in_transaction():
                await MyModel.create(name='bar')
                # this will rollback to the savepoint, meaning that
                # the 'bar' record will not be created, however,
                # the 'foo' record will be created
                raise Exception()
        except Exception:
            pass

When using ``asyncio.gather`` or similar ways to spin up concurrent tasks in a transaction block,
avoid having nested transaction blocks in the concurrent tasks. Transactions are stateful and nested
blocks are expected to run sequentially, not concurrently.


.. automodule:: tortoise.transactions
    :members:
    :undoc-members:
