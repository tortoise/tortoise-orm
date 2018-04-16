=========
Query API
=========

Be sure to check `examples <https://github.com/Zeliboba5/tortoise-orm/tree/master/examples>`_ for better understanding

You start your query from your model instance:

.. code-block:: python

    Event.filter(id=1)

There are several method on model itself to start query:

- ``first(*args, **kwargs)`` - create QuerySet with given filters
- ``all()`` - create QuerySet without filters
- ``first()`` - create QuerySet limited to one object and returning instance instead of list

This method returns ``QuerySet`` object, that allows further filtering and some more complex operations

Also model class have this methods to create object:

- ``create(**kwargs)`` - creates object with given kwargs
- ``get_or_create(defaults, **kwargs)`` - gets object for given kwargs, if not found create it with additional kwargs from defaults dict

Also instance of model itself has these methods:

- ``save()`` - update instance, or insert it, if it was never saved before
- ``delete()`` - delete instance from db
- ``fetch_related(*args)`` - fetches objects related to instance. It can fetch fk relation, backward fk realtion and m2m relation. It also can fetch variable depth of related objects like this: ``await team.fetch_related('events__tournament')`` - this will fetch all events for team, and for each of this events their tournament will be prefetched too. After fetching objects they should be available normally like this: ``team.events[0].tournament.name``

Another approach to work with related objects on instance is to query them explicitly in ``async for``:

.. code-block:: python

    async for team in event.participants:
        print(team.name)

You also can filter related objects like this:

await team.events.filter(name='First')

which will return you a QuerySet object with predefined filter

QuerySet
========

After you obtained queryset from object you can do following operations with it:

- ``filter(*args, **kwargs)`` - filters QuerySet by given kwargs. You can filter by related objects like this: ``Team.filter(events__tournament__name='Test')``. You can also pass ``Q`` objects to ``filters`` as args.
- ``order_by(*args)`` - accept args to filter by in format like ``.order_by('name', '-tournament__name')``. Supports ordering by related models too.
- ``limit(limit)`` - limits QuerySet by given int
- ``offset(offset)`` - offset for QuerySet
- ``distinct()`` - make QuerySet distinct
- ``values_list(*args, flat=False)`` - make QuerySet returns list of tuples for given args instead of objects. If ``flat`` is  ``True`` and only one arg is passed can return flat list
- ``values(*args)`` - make QuerySet return dicts instead of objects
- ``delete()`` - deletes all objects in QuerySet
- ``update(**kwargs)`` - updates all objects in QuerySet with given kwargs
- ``count()`` - returns count of objects in queryset instead of objects
- ``first()`` - limit queryset to one object and return one object instead of list
- ``prefetch_related(*args)`` - like ``.fetch_related()`` on instance, but works on all objects in QuerySet.
- ``using_db(client)`` - executes query in other db client. Useful for transactions workaround.
- ``annotate(**kwargs)`` - annotates result with aggregation result

After making your QuerySet you just have to ``await`` it to get the result

Check `examples <https://github.com/Zeliboba5/tortoise-orm/tree/master/examples>`_ to see it all in work

Many to Many
============

Tortoise provides api for working with M2M relations
- ``add(*args)`` - adds instances to relation
- ``remove(*args)`` - removes instances from relation
- ``clear()`` - removes all objects from relation

You can use them like this:

.. code-block:: python

    await event.participants.add(participant_1, participant_2)



Q objects
=========

When you need to make ``OR`` query or something a little more challenging you could use Q objects for it. It is as easy as this:

.. code-block:: python

    found_events = await Event.filter(
        Q(id__in=[event_first.id, event_second.id]) | Q(name='3')
    )



Filtering
=========

When using ``.filter()`` method you can use number of modifiers to field names to specify desired operation

.. code-block:: python

    teams = await Team.filter(name__icontains='CON')


- ``in`` - checks if value of field is in passed list
- ``not_in``
- ``gte`` - greater or equals than passed value
- ``gt`` - greater than passed value
- ``lte`` - lower or equals than passed value
- ``lt`` - lower than passed value
- ``isnull`` - field is null
- ``not_isnull``
- ``contains`` - field contains specified substring
- ``icontains`` - case insensitive ``contains``
- ``startswith`` - if field starts with value
- ``istartswith`` - case insensitive ``startswith``
- ``endswith`` - if field ends with value
- ``iendswith`` - case insensitive ``endswith``


Complex prefetch
================

Sometimes it is required to fetch only certain related records. You can achieve it with ``Prefetch`` object

.. code-block:: python

    tournament_with_filtered = await Tournament.all().prefetch_related(
        Prefetch('events', queryset=Event.filter(name='First'))
    ).first()

You can view full example here: `examples <https://github.com/Zeliboba5/tortoise-orm/tree/master/examples/complex_prefetching.py>`_