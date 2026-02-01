.. _models:

======
Models
======

.. rst-class:: emphasize-children

Usage
=====

All models should be derived from ``Model``. To start describing the models, import ``Model`` from ``tortoise.models``.

.. code-block:: python3

    from tortoise.models import Model

With that start describing the models

.. code-block:: python3

    class Tournament(Model):
        id = fields.IntField(primary_key=True)
        name = fields.TextField()
        created = fields.DatetimeField(auto_now_add=True)

        def __str__(self):
            return self.name


    class Event(Model):
        id = fields.IntField(primary_key=True)
        name = fields.TextField()
        tournament = fields.ForeignKeyField('models.Tournament', related_name='events')
        participants = fields.ManyToManyField('models.Team', related_name='events', through='event_team')
        modified = fields.DatetimeField(auto_now=True)
        prize = fields.DecimalField(max_digits=10, decimal_places=2, null=True)

        def __str__(self):
            return self.name


    class Team(Model):
        id = fields.IntField(primary_key=True)
        name = fields.TextField()

        def __str__(self):
            return self.name

Let's look at the details of what we accomplished here:

.. code-block:: python3

    class Tournament(Model):

Every model should be derived from ``Model`` or its subclasses. Custom ``Model`` subclasses can be created in the following way:

.. code-block:: python3

    class AbstractTournament(Model):
        id = fields.IntField(primary_key=True)
        name = fields.TextField()
        created = fields.DatetimeField(auto_now_add=True)

        class Meta:
            abstract = True

        def __str__(self):
            return self.name

This model will not affect the schema, but it will be available for inheritance.


Further we have field ``fields.DatetimeField(auto_now=True)``. Options ``auto_now`` and ``auto_now_add`` work like Django's options.

Use of ``__models__``
---------------------

If you define the variable ``__models__`` in the module which you load your models from, ``generate_schema`` will use that list, rather than automatically finding models for you.

Primary Keys
------------

In Tortoise ORM, every model must have a primary key.

That primary key will be accessible through a reserved field ``pk`` which will be an alias of whichever field has been nominated as a primary key.
That alias field can be used as a field name when doing filtering e.g. ``.filter(pk=...)`` etc…

.. note::

    We currently support single (non-composite) primary keys of any indexable field type, but only these field types are recommended:

.. code-block:: python3

    IntField
    BigIntField
    CharField
    UUIDField

One must define a primary key by setting the ``primary_key`` parameter to ``True``.
If you don't define a primary key, the primary key will be generated as an ``IntField`` with name of ``id``.

.. note::
   If this is used on an Integer Field, ``generated`` will be set to ``True`` unless you explicitly pass ``generated=False`` as well.

Any of these are valid primary key definitions:

.. code-block:: python3

    id = fields.IntField(primary_key=True)

    checksum = fields.CharField(primary_key=True)

    guid = fields.UUIDField(primary_key=True)


Inheritance
-----------

When defining models in Tortoise ORM, you can save a lot of
repetitive work by leveraging from inheritance.

You can define fields in more generic classes and they are
automatically available in derived classes. Base classes are
not limited to Model classes. Any class will work. This way
you are able to define your models in a natural and easy
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
        id = fields.IntField(primary_key=True)

        class Meta:
            abstract = True

    class UserModel(TimestampMixin, MyAbstractBaseModel):
        # Overriding the id definition
        # from MyAbstractBaseModel
        id = fields.UUIDField(primary_key=True)

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

    .. attribute:: schema
        :annotation: = ""

        Set this to configure a schema name, where table exists

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
            unique_together=(("field_a", "field_b"), ("field_c", "field_d", "field_e"))

    .. attribute:: indexes
        :annotation: = None

        Specify ``indexes`` to set up compound non-unique indexes for sets of columns.

        It should be a tuple of tuples (lists are fine) in the format of:

        .. code-block:: python3

            indexes=("field_a", "field_b")
            indexes=(("field_a", "field_b"), )
            indexes=(("field_a", "field_b"), ("field_c", "field_d", "field_e"))

    .. attribute:: ordering
        :annotation: = None

        Specify ``ordering`` to set up default ordering for given model.
        It should be iterable of strings formatted in same way as ``.order_by(...)`` receives.
        If query is built with ``GROUP_BY`` clause using ``.annotate(...)`` default ordering is not applied.

        .. code-block:: python3

            ordering = ["name", "-score"]

    .. attribute:: manager
        :annotation: = tortoise.manager.Manager

        Specify ``manager`` to override the default manager.
        It should be instance of ``tortoise.manager.Manager`` or subclass.

        .. code-block:: python3

            manager = CustomManager()

``ForeignKeyField``
-------------------

.. code-block:: python3

    tournament = fields.ForeignKeyField('models.Tournament', related_name='events')
    participants = fields.ManyToManyField('models.Team', related_name='events')
    modified = fields.DatetimeField(auto_now=True)
    prize = fields.DecimalField(max_digits=10, decimal_places=2, null=True)

In event model we got some more fields, that could be interesting for us.

``fields.ForeignKeyField('models.Tournament', related_name='events')``
    Here we create foreign key reference to tournament. We create it by referring to model by it's literal, consisting of app name and model name. ``models`` is default app name, but you can change it in ``class Meta`` with ``app = 'other'``.
``related_name``
    Is keyword argument, that defines field for related query on referenced models, so with that you could fetch all tournaments's events with like this:

.. code-block:: python3

    await Tournament.first().prefetch_related("events")

The DB-backing field
^^^^^^^^^^^^^^^^^^^^

.. note::

    A ``ForeignKeyField`` is a virtual field, meaning it has no direct DB backing.
    Instead it has a field (by default called :samp:`{FKNAME}_id` (that is, just an ``_id`` is appended)
    that is the actual DB-backing field.

    It will just contain the Key value of the related table.

    This is an important detail as it would allow one to assign/read the actual value directly,
    which could be considered an optimization if the entire foreign object isn't needed.


Specifying an FK can be done via either passing the object:

.. code-block::  python3

    await SomeModel.create(tournament=the_tournament)
    # or
    somemodel.tournament=the_tournament

or by directly accessing the DB-backing field:

.. code-block::  python3

    await SomeModel.create(tournament_id=the_tournament.pk)
    # or
    somemodel.tournament_id=the_tournament.pk


Querying a relationship is typically done by appending a double underscore, and then the foreign object's field. Then a normal query attr can be appended.
This can be chained if the next key is also a foreign object:

    :samp:`{FKNAME}__{FOREIGNFIELD}__gt=3`

    or

    :samp:`{FKNAME}__{FOREIGNFK}__{VERYFOREIGNFIELD}__gt=3`

There is however one major limitation. We don't want to restrict foreign column names, or have ambiguity (e.g. a foreign object may have a field called ``isnull``)

Then this would be entirely ambiguous:

    :samp:`{FKNAME}__isnull`

To prevent that we require that direct filters be applied to the DB-backing field of the foreign key:

    :samp:`{FKNAME}_id__isnull`

Fetching the foreign object
^^^^^^^^^^^^^^^^^^^^^^^^^^^

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


To get the Reverse-FK, e.g. an `event.tournament` we currently only support the sync interface.

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

Improving relational type hinting
=================================

Since Tortoise ORM is still a young project, it does not have such widespread support by
various editors who help you writing code using good autocomplete for models and
different relations between them.
However, you can get such autocomplete by doing a little work yourself.
All you need to do is add a few annotations to your models for fields that are responsible
for the relations.

Here is an updated example from :ref:`getting_started`, that will add autocomplete for
all models including fields for the relations between models.

.. code-block:: python3

    from tortoise.models import Model
    from tortoise import fields


    class Tournament(Model):
        id = fields.IntField(primary_key=True)
        name = fields.CharField(max_length=255)

        events: fields.ReverseRelation["Event"]

        def __str__(self):
            return self.name


    class Event(Model):
        id = fields.IntField(primary_key=True)
        name = fields.CharField(max_length=255)
        tournament: fields.ForeignKeyRelation[Tournament] = fields.ForeignKeyField(
            "models.Tournament", related_name="events"
        )
        participants: fields.ManyToManyRelation["Team"] = fields.ManyToManyField(
            "models.Team", related_name="events", through="event_team"
        )

        def __str__(self):
            return self.name


    class Team(Model):
        id = fields.IntField(primary_key=True)
        name = fields.CharField(max_length=255)

        events: fields.ManyToManyRelation[Event]

        def __str__(self):
            return self.name


Reference
=========

.. automodule:: tortoise.models
    :members: Model
    :undoc-members:
