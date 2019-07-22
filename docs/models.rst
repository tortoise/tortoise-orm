.. _models:

======
Models
======

Usage
=====

To get working with models, first you should import them

.. code-block:: python3

    from tortoise.models import Model

With that you can start describing your own models like that

.. code-block:: python3

    class Tournament(Model):
        id = fields.IntField(pk=True)
        name = fields.TextField()
        created = fields.DatetimeField(auto_now_add=True)

        def __str__(self):
            return self.name


    class Event(Model):
        id = fields.IntField(pk=True)
        name = fields.TextField()
        tournament = fields.ForeignKeyField('models.Tournament', related_name='events')
        participants = fields.ManyToManyField('models.Team', related_name='events', through='event_team')
        modified = fields.DatetimeField(auto_now=True)
        prize = fields.DecimalField(max_digits=10, decimal_places=2, null=True)

        def __str__(self):
            return self.name


    class Team(Model):
        id = fields.IntField(pk=True)
        name = fields.TextField()

        def __str__(self):
            return self.name

Let see in details what we accomplished here:

.. code-block:: python3

    class Tournament(Model):

Every model should be derived from base model. You also can derive from your own model subclasses and you can make abstract models like this

.. code-block:: python3

    class AbstractTournament(Model):
        id = fields.IntField(pk=True)
        name = fields.TextField()
        created = fields.DatetimeField(auto_now_add=True)

        class Meta:
            abstract = True

        def __str__(self):
            return self.name

This models won't be created in schema generation and won't create relations to other models.


Further we have field ``fields.DatetimeField(auto_now=True)``. Options ``auto_now`` and ``auto_now_add`` work like Django's options.

Use of ``__models__``
---------------------

If you define the variable ``__models__`` in the module which you load your models from, ``generate_schema`` will use that list, rather than automatically finding models for you.

Primary Keys
------------

In Tortoise ORM we require that a model has a primary key.

That primary key will be accesible through a reserved field ``pk`` which will be an alias of whichever field has been nominated as a primary key.
That alias field can be used as a field name when doing filtering e.g. ``.filter(pk=...)`` etc...

We currently support single (non-composite) primary keys of any indexable field type, but only these field types are recommended:

.. code-block:: python3

    IntField
    BigIntField
    CharField
    UUIDField

One must define a primary key by setting a ``pk`` parameter to ``True``.

If you don't define a primary key, we will create a primary key of type ``IntField`` with name of ``id`` for you.

Any of these are valid primary key definitions in a Model:

.. code-block:: python3

    id = fields.IntField(pk=True)

    checksum = fields.CharField(pk=True)

    guid = fields.UUIDField(pk=True)


Inheritence
-----------

When defining models in Tortoise ORM, you can save a lot of
repetitive work by leveraging from inheritence.

You can define fields in more generic classes and they are
automatically available in derived classes. Base classes are
not limited to Model classes. Any class will work. This way
you are able to define your models in a very natural and easy
to maintain way.

Let's have a look at some examples.

.. code-block:: python3

    from tortoise import fields
    from tortoise.models import Model

    class TimestampMixin():
        created_at = fields.DatetimeField(null=True, auto_now_add=True)
        modified_at = fields.DatetimeField(null=True, auto_now=True)

    class NameMixin():
        name = fields.CharField(40, unique=True)

    class MyAbstractBaseModel(Model):
        id = fields.IntField(pk=True)

        class Meta:
            abstract = True

    class UserModel(TimestampMixin, MyAbstractBaseModel):
        # Overriding the id definition
        # from MyAbstractBaseModel
        id = fields.UUIDField(pk=True)

        # Adding additional fields
        first_name = fields.CharField(20, null=True)

        class Meta:
            table = "user"


    class RoleModel(TimestampMixin, NameMixin, MyAbstractBaseModel):

        class Meta:
            table = "role"

Using the ``Meta`` class is not necessary. But it is a good habit, to
give your table an explicit name. This way you can change the model name
without breaking the schema. So the following definition is valid.

.. code-block:: python3

    class RoleModel(TimestampMixin, NameMixin, MyAbstractBaseModel):
        pass

The ``Meta`` class
------------------

.. autoclass:: tortoise.models.Model.Meta

    .. attribute:: abstract
        :annotation: = False

        Set to ``True`` to indicate this is an abstract class

    .. attribute:: table
        :annotation: = ""

        Set this to configure a manual table name, instead of a generated one

    .. attribute:: table_description
        :annotation: = ""

        Set this to generate a comment message for the table being created for the current model

    .. attribute:: unique_together
        :annotation: = None

        Specify ``unique_together`` to set up compound unique indexes for sets of columns.

        It should be a tuple of tuples (lists are fine) in the format of:

        .. code-block:: python3

            unique_together=("field_a", "field_b")
            unique_together=(("field_a", "field_b"), )
            unique_together=(("field_a", "field_b"), ("field_c", "field_d", "field_e")

``ForeignKeyField``
-------------------

.. code-block:: python3

    tournament = fields.ForeignKeyField('models.Tournament', related_name='events')
    participants = fields.ManyToManyField('models.Team', related_name='events')
    modified = fields.DatetimeField(auto_now=True)
    prize = fields.DecimalField(max_digits=10, decimal_places=2, null=True)

In event model we got some more fields, that could be interesting for us.

``fields.ForeignKeyField('models.Tournament', related_name='events')``
    Here we create foreign key reference to tournament. We create it by referring to model by it's literal, consisting of app name and model name. `models` is default app name, but you can change it in `class Meta` with `app = 'other'`.
``related_name``
    Is keyword argument, that defines field for related query on referenced models, so with that you could fetch all tournaments's events with like this:

Fetching foreign keys can be done with both async and sync interfaces.

Async fetch:

.. code-block:: python3

    events = await tournament.events.all()

You can async iterate over it like this:

.. code-block:: python3

    async for event in tournament.events:
        ...

Sync usage requires that you call `fetch_related` before the time, and then you can use common functions such as:

.. code-block:: python3

    await tournament.fetch_related('events')
    events = list(tournament.events)
    eventlen = len(tournament.events)
    if SomeEvent in tournament.events:
        ...
    if tournament.events:
        ...
    firstevent = tournament.events[0]


To get the reverse fk, e.g. an `event.tournament` we currently only support the sync interface.

.. code-block:: python3

    await event.fetch_related('tournament')
    tournament = event.tournament


``ManyToManyField``
-------------------

Next field is ``fields.ManyToManyField('models.Team', related_name='events')``. It describes many to many relation to model Team.

To add to a ``ManyToManyField`` both the models need to be saved, else you will get an ``OperationalError`` raised.

Resolving many to many fields can be done with both async and sync interfaces.

Async fetch:

.. code-block:: python3

    participants = await tournament.participants.all()

You can async iterate over it like this:

.. code-block:: python3

    async for participant in tournament.participants:
        ...

Sync usage requires that you call `fetch_related` before the time, and then you can use common functions such as:

.. code-block:: python3

    await tournament.fetch_related('participants')
    participants = list(tournament.participants)
    participantlen = len(tournament.participants)
    if SomeParticipant in tournament.participants:
        ...
    if tournament.participants:
        ...
    firstparticipant = tournament.participants[0]

The reverse lookup of ``team.event_team`` works exactly the same way.


Reference
=========

.. automodule:: tortoise.models
    :members: Model
    :undoc-members:
