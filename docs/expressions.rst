.. _expressions:

===========
Expressions
===========

F expression
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
