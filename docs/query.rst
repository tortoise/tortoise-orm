.. _query_api:

=========
Query API
=========

This document describes how to use QuerySet to build your queries

Be sure to check `examples <https://github.com/tortoise/tortoise-orm/tree/master/examples>`_ for better understanding

You start your query from your model class:

.. code-block:: python3

    Event.filter(id=1)

There are several method on model itself to start query:

- ``filter(*args, **kwargs)`` - create QuerySet with given filters
- ``exclude(*args, **kwargs)`` - create QuerySet with given excluding filters
- ``all()`` - create QuerySet without filters
- ``first()`` - create QuerySet limited to one object and returning instance instead of list
- ``annotate()`` - create QuerySet with given annotation

This method returns ``QuerySet`` object, that allows further filtering and some more complex operations

Also model class have this methods to create object:

- ``create(**kwargs)`` - creates object with given kwargs
- ``get_or_create(defaults, **kwargs)`` - gets object for given kwargs, if not found create it with additional kwargs from defaults dict

Also instance of model itself has these methods:

- ``save()`` - update instance, or insert it, if it was never saved before
- ``delete()`` - delete instance from db
- ``fetch_related(*args)`` - fetches objects related to instance. It can fetch FK relation, Backward-FK relations and M2M relations. It also can fetch variable depth of related objects like this: ``await team.fetch_related('events__tournament')`` - this will fetch all events for team, and for each of this events their tournament will be prefetched too. After fetching objects they should be available normally like this: ``team.events[0].tournament.name``

Another approach to work with related objects on instance is to query them explicitly in ``async for``:

.. code-block:: python3

    async for team in event.participants:
        print(team.name)

You also can filter related objects like this:

.. code-block:: python3

    await team.events.filter(name='First')

which will return you a QuerySet object with predefined filter

QuerySet
========

After you obtained queryset from object you can do following operations with it:

.. automodule:: tortoise.queryset
    :members:
    :exclude-members: QuerySetSingle, QuerySet, AwaitableQuery

    .. autoclass:: QuerySetSingle

    .. autoclass:: QuerySet
        :inherited-members:

QuerySet could be constructed, filtered and passed around without actually hitting database.
Only after you ``await`` QuerySet, it will generate query and run it against database.

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

    # Fetched result for m2m and backward fk relations are stored in list-like container
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
    await Tournament.annotate(clean_name=Trim('name'))).filter(clean_name='tournament')
    await Tournament.annotate(name_upper=Upper('name'))).filter(name_upper='TOURNAMENT')
    await Tournament.annotate(name_lower=Lower('name'))).filter(name_lower='tournament')
    await Tournament.annotate(desc_clean=Coalesce('desc', ''))).filter(desc_clean='')

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


Q objects
=========

Sometimes you need to do more complicated queries than the simple AND ``<model>.filter()`` provides. Luckily we have Q objects to spice things up and help you find what you need. These Q-objects can then be used as argument to ``<model>.filter()`` instead.

Q objects are extremely versatile, some example use cases:
 - creating an OR filter
 - nested filters
 - inverted filters
 - combining any of the above to simply write complicated multilayer filters

Q objects can take any (special) kwargs for filtering that ``<model>.filter()`` accepts, see those docs for a full list of filter options in that regard.

They can also be combined by using bitwise operators (``|`` is OR and ``&`` is AND for those unfamiliar with bitwise operators)

For example to find the events with as name ``Event 1`` or ``Event 2``:

.. code-block:: python3

    found_events = await Event.filter(
        Q(name='Event 1') | Q(name='Event 2')
    )

Q objects can be nested as well, the above for example is equivalent to:

.. code-block:: python3

    found_events = await Event.filter(
        Q(Q(name='Event 1'), Q(name='Event 2'), join_type="OR")
    )

If join type is omitted it defaults to ``AND``.

.. note::
    Q objects without filter arguments are considered NOP and will be ignored for the final query (regardless on if they are used as ``AND`` or ``OR`` param)


Also, Q objects support negated to generate ``NOT`` (``~`` operator) clause in your query

.. code-block:: python3

    not_third_events = await Event.filter(~Q(name='3'))

.. automodule:: tortoise.query_utils
    :members: Q, QueryModifier
    :undoc-members:


.. _filtering-queries:

Filtering
=========

When using ``.filter()`` method you can use number of modifiers to field names to specify desired operation

.. code-block:: python3

    teams = await Team.filter(name__icontains='CON')

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
