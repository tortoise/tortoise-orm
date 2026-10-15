=======
Signals
=======

There are four signals that defined now, they will be send by models.

Listeners registered on a model also receive signals from its subclasses,
including listeners registered on abstract base models. The sender passed to a
listener is the concrete model class. A listener registered on more than one
class in the inheritance hierarchy is called once per signal. Listeners run
concurrently, so their completion order is not guaranteed.

.. automodule:: tortoise.signals
    :members:
    :undoc-members:
    :show-inheritance:
