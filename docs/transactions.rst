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


Running Code After Commit
=========================

``on_commit()`` defers a callback until the current transaction commits. Use it for side
effects that must only happen once the data is visible to other connections.

  .. code-block:: python3

    async with in_transaction():
        order = await Order.create(status="paid")

        async def send_receipt() -> None:
            await mailer.send_receipt(order.id)

        # runs after the outermost block commits, and never if it rolls back
        await on_commit(send_receipt)

The callback takes no arguments and may be sync or async. Callbacks registered in a nested
block are dropped if that block rolls back to its savepoint, and otherwise wait for the
outermost block. They run in registration order, once the connection is released, so they
can query the database. Outside a transaction, the callback runs immediately.

Every callback runs, even if an earlier one raises. The exceptions are then raised together
in an ``ExceptionGroup``, which you can handle with ``except*``.


.. automodule:: tortoise.transactions
    :members:
    :undoc-members:
