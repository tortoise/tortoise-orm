.. _transactions:

============
Transactions
============

.. note::
   Tortoise uses contextvars (and it's polyfill `aiocontextvars
   <https://github.com/fantix/aiocontextvars>`_) to manage transactions.
   Which means, that automatic propagation of transactions could be achieved only
   in same task context. If you are going to spawn more tasks through
   ``asyncio.ensure_future()`` (or any other method to spawn tasks) transactions won't be
   propagated. But in such cases you can explicitly pass transaction instance
   to method you are calling, like this:

    .. code-block:: python3

        async with in_transaction() as tr:
            await asyncio.gather(*[Tournament.create(name="Test", using_db=tr) for _ in range(100)])




.. automodule:: tortoise.transactions
    :members:
    :undoc-members:
