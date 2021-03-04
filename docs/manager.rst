.. _manager:

=======
Manager
=======

A Manager is the interface through which database query operations are provided to tortoise models.

There is one default Manager for every tortoise model.

Usage
=====

There are two ways to use a Manager, one is use `manager` in `Meta` to override the default `manager`, another is define manager in model:

.. code-block:: python3

    from tortoise.manager import Manager

    class StatusManager(Manager):
        def get_queryset(self):
            return super(StatusManager, self).get_queryset().filter(status=1)


    class ManagerModel(Model):
        status = fields.IntField(default=0)
        all_objects = Manager()

        class Meta:
            manager = StatusManager()


After override default manager, all queries like `Model.get()`, `Model.filter()` will be comply with the behavior of custom manager.

In the example above, you can never get the objects which status is equal to `0` with default manager, but you can use the manager `all_objects` defined in model to get all objects.

.. code-block:: python3

    m1 = await ManagerModel.create()
    m2 = await ManagerModel.create(status=1)

    self.assertEqual(await ManagerModel.all().count(), 1)
    self.assertEqual(await ManagerModel.all_objects.count(), 2)

    self.assertIsNone(await ManagerModel.get_or_none(pk=m1.pk))
    self.assertIsNotNone(await ManagerModel.all_objects.get_or_none(pk=m1.pk))
    self.assertIsNotNone(await ManagerModel.get_or_none(pk=m2.pk))
