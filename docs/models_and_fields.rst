=================
Models and fields 
=================
To get working with models, first you should import them 
 from tortoise.models import Model

With that you can start describing your own models like that

.. code-block:: python

    class Tournament(Model):
        id = fields.IntField(pk=True)
        name = fields.StringField()
        created = fields.DatetimeField(auto_now_add=True)

        def __str__(self):
            return self.name


    class Event(Model):
        id = fields.IntField(pk=True)
        name = fields.StringField()
        tournament = fields.ForeignKeyField('models.Tournament', related_name='events')
        participants = fields.ManyToManyField('models.Team', related_name='events', through='event_team')
        modified = fields.DatetimeField(auto_now=True)
        prize = fields.DecimalField(max_digits=10, decimal_places=2, null=True)

        def __str__(self):
            return self.name


    class Team(Model):
        id = fields.IntField(pk=True)
        name = fields.StringField()

        def __str__(self):
            return self.name

Let see in details what we accomplished here:

.. code-block:: python

    class Tournament(Model):

Every model should be derived from base model. You also can derive from your own model subclasses and you can make abstract models like this

.. code-block:: python

    class AbstractTournament(Model):
        id = fields.IntField(pk=True)
        name = fields.StringField()
        created = fields.DatetimeField(auto_now_add=True)

        class Meta:
            abstract = True

        def __str__(self):
            return self.name

This models won't be created in schema generation and won't create relations to other models.

Further, let's take a look at created fields for models

.. code-block:: python

    id = fields.IntField(pk=True)

This code defines integer primary key for table. Sadly, currently only simple integer pk is supported.

.. code-block:: python

    tournament = fields.ForeignKeyField('models.Tournament', related_name='events')
    participants = fields.ManyToManyField('models.Team', related_name='events', through='event_team')
    modified = fields.DatetimeField(auto_now=True)
    prize = fields.DecimalField(max_digits=10, decimal_places=2, null=True)

In event model we got some more fields, that could be interesting for us. 
``fields.ForeignKeyField('models.Tournament', related_name='events')`` - here we create foreign key reference to tournament. We create it by referring to model by it's literal, consisting of app name and model name. `models` is default app name, but you can change it in `class Meta` with `app = 'other'`.
``related_name`` is keyword argument, that defines field for related query on referenced models, so with that you could fetch all tournaments's events with like this:

.. code-block:: python

    await tournament.events.all()

or like this:

.. code-block:: python

    await tournament.fetch_related('events')


Next field is ``fields.ManyToManyField('models.Team', related_name='events', through='event_team')``. It describes many to many relation to model Team.
Here we have additional kwarg ``through`` that defines name of intermediate table.

Further we have field ``fields.DatetimeField(auto_now=True)``. Options ``auto_now`` and ``auto_now_add`` work like Django's options.

Init app
========

After you defined all your models, tortoise needs you to init them, in order to create backward relations between models and match your db client with appropriate models.

You can do it like this:

.. code-block:: python

    from tortoise.backends.asyncpg.client import AsyncpgDBClient
    from tortoise import Tortoise
    from app import models # without importing models Tortoise can't find and init them


    async def init():
        db = AsyncpgDBClient(
            host='localhost',
            port=5432,
            user='postgres',
            password='qwerty123',
            database='events',
       )
        
        await db.create_connection()
        Tortoise.init(db)
        
        await generate_schema(client)

Here we create connection to database with default asyncpg client and then we init models. Be sure that you have your models imported in the app. Usually that's the case, because you use your models across you app, but if you have only local imports of it, tortoise won't be able to find them and init them with connection to db.
``generate_schema`` generates schema on empty database, you shouldn't run it on every app init, run it just once, maybe out of your main code.


Fields
======

Here is list of fields available at the moment with custom options of this fields:

- IntField (``pk``)
- SmallIntField
- StringField
- BooleanField
- DecimalField (``max_digits``, ``decimal_places``)
- DatetimeField (``auto_now``, ``auto_now_add``)
- DateField
- ForeignKeyField (model_name, related_name, on_delete)
- ManyToManyField (``model_name``, ``related_name``, ``through``, ``backward_key``, ``forward_key``)

Also all fields fields have this options:
- ``source_field`` - field name in schema, can be different from field name
- ``null`` - is field nullable
- ``default`` - default value for field
- ``generated`` - flag that says that this field is read only and value should be generated in db. Normally, should be used only if you working on already created schema, not generated by tortoise.

