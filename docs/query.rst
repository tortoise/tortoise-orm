.. _query_api:

=========
Query API
=========

This document describes how to use QuerySet to query the database.

Be sure to check `examples <https://github.com/tortoise/tortoise-orm/tree/master/examples>`_.

Below is an example of a simple query that will return all events with a rating greater than 5:

.. code-block:: python3

    await Event.filter(rating__gt=5)

There are several method on model itself to start query:

- ``filter(*args, **kwargs)`` - create QuerySet with given filters
- ``exclude(*args, **kwargs)`` - create QuerySet with given excluding filters
- ``all()`` - create QuerySet without filters
- ``first()`` - create QuerySet limited to one object and returning the first object
- ``annotate()`` - create QuerySet with given annotation

The methods above return a ``QuerySet`` object, which supports chaining query operations.

The following methods can be used to create an object:

- ``create(**kwargs)`` - creates an object with given kwargs
- ``get_or_create(defaults, **kwargs)`` - gets an object for given kwargs, if not found create it with additional kwargs from defaults dict

The instance of a model has the following methods:

- ``save()`` - update instance, or insert it, if it was never saved before
- ``delete()`` - delete instance from db
- ``fetch_related(*args)`` - fetches objects related to instance. It can fetch FK relation, Backward-FK relations and M2M relations. It also can fetch variable depth of related objects like this: ``await team.fetch_related('events__tournament')`` - this will fetch all events for team, and for each of this events their tournament will be prefetched too. After fetching objects they should be available normally like this: ``team.events[0].tournament.name``

Another approach to work with related objects on instance is to query them explicitly with ``async for``:

.. code-block:: python3

    async for team in event.participants:
        print(team.name)

The related objects can be filtered:

.. code-block:: python3

    await team.events.filter(name='First')

which will return you a QuerySet object with predefined filter

QuerySet
========

Once you have a QuerySet, you can perform the following operations with it:

.. automodule:: tortoise.queryset
    :members:
    :exclude-members: QuerySetSingle, QuerySet, AwaitableQuery

    .. autoclass:: QuerySetSingle

    .. autoclass:: QuerySet
        :inherited-members:

QuerySet could be constructed, filtered and passed around without actually hitting the database.
Only after you ``await`` QuerySet, it will execute the query.

Here are some common usage scenarios with QuerySet (we are using models defined in :ref:`getting_started`):

Regular select into model instances:

.. code-block:: python3

    await Event.filter(name__startswith='FIFA')

This query will get you all events with ``name`` starting with ``FIFA``, where ``name`` is fields
defined on model, and ``startswith`` is filter modifier. Take note, that modifiers should
be separated by double underscore. You can read more on filter modifiers in ``Filtering``
section of this document.

It's also possible to filter your queries with ``.exclude()``:

.. code-block:: python3

    await Team.exclude(name__icontains='junior')

As more interesting case, when you are working with related data, you could also build your
query around related entities:

.. code-block:: python3

    # getting all events, which tournament name is "World Cup"
    await Event.filter(tournament__name='World Cup')

    # Gets all teams participating in events with ids 1, 2, 3
    await Team.filter(events__id__in=[1,2,3])

    # Gets all tournaments where teams with "junior" in their name are participating
    await Tournament.filter(event__participants__name__icontains='junior').distinct()


Usually you not only want to filter by related data, but also get that related data as well.
You could do it using ``.prefetch_related()``:

.. code-block:: python3

    # This will fetch events, and for each of events ``.tournament`` field will be populated with
    # corresponding ``Tournament`` instance
    await Event.all().prefetch_related('tournament')

    # This will fetch tournament with their events and teams for each event
    tournament_list = await Tournament.all().prefetch_related('events__participants')

    # Fetched result for m2m and backward fk relations are stored in list-like containe#r
    for tournament in tournament_list:
        print([e.name for e in tournament.events])


General rule about how ``prefetch_related()`` works is that each level of depth of related models
produces 1 additional query, so ``.prefetch_related('events__participants')`` will produce two
additional queries to fetch your data.

Sometimes, when performance is crucial, you don't want to make additional queries like this.
In cases like this you could use ``values()`` or ``values_list()`` to produce more efficient query

.. code-block:: python3

    # This will return list of dicts with keys 'id', 'name', 'tournament_name' and
    # 'tournament_name' will be populated by name of related tournament.
    # And it will be done in one query
    events = await Event.filter(id__in=[1,2,3]).values('id', 'name', tournament_name='tournament__name')

QuerySet also supports aggregation and database functions through ``.annotate()`` method

.. code-block:: python3

    from tortoise.functions import Count, Trim, Lower, Upper, Coalesce

    # This query will fetch all tournaments with 10 or more events, and will
    # populate filed `.events_count` on instances with corresponding value
    await Tournament.annotate(events_count=Count('events')).filter(events_count__gte=10)
    await Tournament.annotate(clean_name=Trim('name')).filter(clean_name='tournament')
    await Tournament.annotate(name_upper=Upper('name')).filter(name_upper='TOURNAMENT')
    await Tournament.annotate(name_lower=Lower('name')).filter(name_lower='tournament')
    await Tournament.annotate(desc_clean=Coalesce('desc', '')).filter(desc_clean='')

Check `examples <https://github.com/tortoise/tortoise-orm/tree/master/examples>`_ to see it all in work

.. _foreign_key:

Foreign Key
===========

Tortoise ORM provides an API for working with FK relations

.. autoclass:: tortoise.fields.relational.ReverseRelation
    :members:

.. autodata:: tortoise.fields.relational.ForeignKeyNullableRelation

.. autodata:: tortoise.fields.relational.ForeignKeyRelation

.. _one_to_one:

One to One
==========

.. autodata:: tortoise.fields.relational.OneToOneNullableRelation

.. autodata:: tortoise.fields.relational.OneToOneRelation

.. _many_to_many:

Many to Many
============

Tortoise ORM provides an API for working with M2M relations

.. autoclass:: tortoise.fields.relational.ManyToManyRelation
    :members:
    :inherited-members:

You can use them like this:

.. code-block:: python3

    await event.participants.add(participant_1, participant_2)


.. _filtering-queries:

Filtering
=========

When using the ``.filter()`` method, you can apply various modifiers to field names to specify the desired lookup type.
In the following example, we filter the Team model to find all teams whose names contain the string CON (case-insensitive):

.. code-block:: python3

    teams = await Team.filter(name__icontains='CON')

The following lookup types are available:

- ``not``
- ``in`` - checks if value of field is in passed list
- ``not_in``
- ``gte`` - greater or equals than passed value
- ``gt`` - greater than passed value
- ``lte`` - lower or equals than passed value
- ``lt`` - lower than passed value
- ``range`` - between and given two values
- ``isnull`` - field is null
- ``not_isnull`` - field is not null
- ``contains`` - field contains specified substring
- ``icontains`` - case insensitive ``contains``
- ``startswith`` - if field starts with value
- ``istartswith`` - case insensitive ``startswith``
- ``endswith`` - if field ends with value
- ``iendswith`` - case insensitive ``endswith``
- ``iexact`` - case insensitive equals
- ``search`` - full text search

For PostgreSQL and MySQL, the following date related lookup types are available:

- ``year`` - e.g. ``await Team.filter(created_at__year=2020)``
- ``quarter``
- ``month``
- ``week``
- ``day``
- ``hour``
- ``minute``
- ``second``
- ``microsecond``


In PostgreSQL and MYSQL, you can use the ``contains``, ``contained_by`` and ``filter`` options in ``JSONField``.
The ``filter`` option allows you to filter the JSON object by its keys and values.

.. code-block:: python3

    class JSONModel:
        data = fields.JSONField[list]()

    await JSONModel.create(data=["text", 3, {"msg": "msg2"}])
    obj = await JSONModel.filter(data__contains=[{"msg": "msg2"}]).first()

    await JSONModel.create(data=["text"])
    await JSONModel.create(data=["tortoise", "msg"])
    await JSONModel.create(data=["tortoise"])

    objects = await JSONModel.filter(data__contained_by=["text", "tortoise", "msg"])

    await JSONModel.create(data={"breed": "labrador",
                                 "owner": {
                                     "name": "Boby",
                                     "last": None,
                                     "other_pets": [
                                         {
                                             "name": "Fishy",
                                         }
                                     ],
                                 },
                             })

    obj1 = await JSONModel.filter(data__filter={"breed": "labrador"}).first()
    obj2 = await JSONModel.filter(data__filter={"owner__name": "Boby"}).first()
    obj3 = await JSONModel.filter(data__filter={"owner__other_pets__0__name": "Fishy"}).first()
    obj4 = await JSONModel.filter(data__filter={"breed__not": "a"}).first()
    obj5 = await JSONModel.filter(data__filter={"owner__name__isnull": True}).first()
    obj6 = await JSONModel.filter(data__filter={"owner__last__not_isnull": False}).first()

In PostgreSQL and MySQL and SQLite, you can use ``posix_regex`` to make comparisons using POSIX regular expressions:
On PostgreSQL, this uses the ``~`` operator, on MySQL and SQLite it uses the ``REGEXP`` operator.
PostgreSQL and SQLite also support ``iposix_regex``, which makes case insensive comparisons.


.. code-block:: python3
    class DemoModel:
      demo_text = fields.TextField()

    await DemoModel.create(demo_text="Hello World")
    obj = await DemoModel.filter(demo_text__posix_regex="^Hello World$").first()
    obj = await DemoModel.filter(demo_text__iposix_regex="^hello world$").first()


With PostgreSQL, for ``JSONField``, ``filter`` supports additional lookup types:

- ``in`` - ``await JSONModel.filter(data__filter={"breed__in": ["labrador", "poodle"]}).first()``
- ``not_in``
- ``gte``
- ``gt``
- ``lte``
- ``lt``
- ``range`` - ``await JSONModel.filter(data__filter={"age__range": [1, 10]}).first()``
- ``startswith``
- ``endswith``
- ``iexact``
- ``icontains``
- ``istartswith``
- ``iendswith``

With PostgreSQL, ``ArrayField`` can be used with the following lookup types:

- ``contains`` - ``await ArrayFields.filter(array__contains=[1, 2, 3]).first()`` which will use the ``@>`` operator
- ``contained_by`` - will use the ``<@`` operator
- ``overlap`` - will use the ``&&`` operator
- ``len`` - will use the ``array_length`` function, e.g. ``await ArrayFields.filter(array__len=3).first()``


Complex prefetch
================

Sometimes it is required to fetch only certain related records. You can achieve it with ``Prefetch`` object:

.. code-block:: python3

    tournament_with_filtered = await Tournament.all().prefetch_related(
        Prefetch('events', queryset=Event.filter(name='First'))
    ).first()

You can view full example here:  :ref:`example_prefetching`

.. autoclass:: tortoise.query_utils.Prefetch
    :members:
