.. _contrib_pydantic:

======================
Pydantic serialisation
======================

Tortoise ORM has a Pydantic plugin that will generate Pydantic Models from Tortoise Models, and then provides helper functions to serialise that model and its related objects.

We currently only support generating Pydantic objects for serialisation, and no deserialisation at this stage.

See the :ref:`examples_pydantic`

Tutorial
========

.. rst-class:: html-toggle

1: Basic usage
--------------

Here we introduce:

* Creating a Pydantic model from a Tortoise model
* Docstrings & doc-comments are used
* Evaluating the generated schema
* Simple serialisation with both ``.dict()`` and ``.json()``

Lets start with a basic Tortoise Model:

.. code-block:: py3

    from tortoise import fields
    from tortoise.models import Model

    class Tournament(Model):
        """
        This references a Tournament
        """
        id = fields.IntField(pk=True)
        name = fields.CharField(max_length=100)
        #: The date-time the Tournament record was created at
        created_at = fields.DatetimeField(auto_now_add=True)

To create a Pydantic model from that one would call ``pydantic_model_creator``:

.. code-block:: py3

    from tortoise.contrib.pydantic import pydantic_model_creator

    Tournament_Pydantic = pydantic_model_creator(Tournament)

And now have a Pydantic Model that can be used for representing schema and serialisation.

The JSON-Schema of ``Tournament_Pydantic`` is now:

.. code-block:: py3

    >>> print(Tournament_Pydantic.schema())
    {
        'title': 'Tournament',
        'description': 'This references a Tournament',
        'type': 'object',
        'properties': {
            'id': {
                'title': 'Id',
                'type': 'integer'
            },
            'name': {
                'title': 'Name',
                'type': 'string'
            },
            'created_at': {
                'title': 'Created At',
                'description': 'The date-time the Tournament record was created at',
                'type': 'string',
                'format': 'date-time'
            }
        }
    }

Note how the class docstring and doc-comment `` #: `` is included as descriptions in the Schema.

To serialise an object it is simply *(in an async context)*:

.. code-block:: py3

    tournament = await Tournament.create(name="New Tournament")
    tourpy = await Tournament_Pydantic.from_tortoise_orm(tournament)

And one could get the contents by using regulat Pydantic-object methods, such as ``.dict()`` or ``.json()``

.. code-block:: py3

    >>> print(tourpy.dict())
    {
        'id': 1,
        'name': 'New Tournament',
        'created_at': datetime.datetime(2020, 3, 1, 20, 28, 9, 346808)
    }
    >>> print(tourpy.json())
    {
        "id": 1,
        "name": "New Tournament",
        "created_at": "2020-03-01T20:28:09.346808"
    }


.. rst-class:: html-toggle

2: Querysets & Lists
--------------------

Here we introduce:

* Creating a list-model to serialise a queryset
* Default sorting is honoured

.. code-block:: py3

    from tortoise import fields
    from tortoise.models import Model

    class Tournament(Model):
        """
        This references a Tournament
        """
        id = fields.IntField(pk=True)
        name = fields.CharField(max_length=100)
        #: The date-time the Tournament record was created at
        created_at = fields.DatetimeField(auto_now_add=True)

        class Meta:
            # Define the default ordering
            #  the pydantic serialiser will use this to order the results
            ordering = ["name"]

To create a Pydantic list-model from that one would call ``pydantic_queryset_creator``:

.. code-block:: py3

    from tortoise.contrib.pydantic import pydantic_model_creator

    Tournament_Pydantic_List = pydantic_queryset_creator(Tournament)

And now have a Pydantic Model that can be used for representing schema and serialisation.

The JSON-Schema of ``Tournament_Pydantic_List`` is now:

.. code-block:: py3

    >>> print(Tournament_Pydantic_List  .schema())
    {
        'title': 'Tournaments',
        'description': 'This references a Tournament',
        'type': 'array',
        'items': {
            '$ref': '#/definitions/Tournament'
        },
        'definitions': {
            'Tournament': {
                'title': 'Tournament',
                'description': 'This references a Tournament',
                'type': 'object',
                'properties': {
                    'id': {
                        'title': 'Id',
                        'type': 'integer'
                    },
                    'name': {
                        'title': 'Name',
                        'type': 'string'
                    },
                    'created_at': {
                        'title': 'Created At',
                        'description': 'The date-time the Tournament record was created at',
                        'type': 'string',
                        'format': 'date-time'
                    }
                }
            }
        }
    }

Note that the ``Tournament`` is now not the root. A simple list is.

To serialise an object it is simply *(in an async context)*:

.. code-block:: py3

    # Create objects
    await Tournament.create(name="New Tournament")
    await Tournament.create(name="Another")
    await Tournament.create(name="Last Tournament")

    tourpy = await Tournament_Pydantic_List.from_queryset(Tournament.all())

And one could get the contents by using regulat Pydantic-object methods, such as ``.dict()`` or ``.json()``

.. code-block:: py3

    >>> print(tourpy.dict())
    {
        '__root__': [
            {
                'id': 2,
                'name': 'Another',
                'created_at': datetime.datetime(2020, 3, 2, 6, 53, 39, 776504)
            },
            {
                'id': 3,
                'name': 'Last Tournament',
                'created_at': datetime.datetime(2020, 3, 2, 6, 53, 39, 776848)
            },
            {
                'id': 1,
                'name': 'New Tournament',
                'created_at': datetime.datetime(2020, 3, 2, 6, 53, 39, 776211)
            }
        ]
    }
    >>> print(tourpy.json())
    [
        {
            "id": 2,
            "name": "Another",
            "created_at": "2020-03-02T06:53:39.776504"
        },
        {
            "id": 3,
            "name": "Last Tournament",
            "created_at": "2020-03-02T06:53:39.776848"
        },
        {
            "id": 1,
            "name": "New Tournament",
            "created_at": "2020-03-02T06:53:39.776211"
        }
    ]

Note how ``.dict()`` has a ``_root__`` element with the list, but the ``.json()`` has the list as root.
Also note how the results are sorted alphabetically by ``name``.


.. rst-class:: html-toggle

3: Relations & Early-init
-------------------------
Here we introduce:

* Relationships
* Early model init

We define our models with a relationship:

.. code-block:: py3

    from tortoise import fields
    from tortoise.models import Model

    class Tournament(Model):
        """
        This references a Tournament
        """

        id = fields.IntField(pk=True)
        name = fields.CharField(max_length=100)
        #: The date-time the Tournament record was created at
        created_at = fields.DatetimeField(auto_now_add=True)

    class Event(Model):
        """
        This references an Event in a Tournament
        """

        id = fields.IntField(pk=True)
        name = fields.CharField(max_length=100)
        created_at = fields.DatetimeField(auto_now_add=True)

        tournament = fields.ForeignKeyField(
            "models.Tournament", related_name="events", description="The Tournement this happens in"
        )

Next we create our Pydantic model using ``pydantic_model_creator``:

.. code-block:: py3

    from tortoise.contrib.pydantic import pydantic_model_creator

    Tournament_Pydantic = pydantic_model_creator(Tournament)

The JSON-Schema of ``Tournament_Pydantic`` is now:

.. code-block:: py3

    >>> print(Tournament_Pydantic.schema())
    {
        'title': 'Tournament',
        'description': 'This references a Tournament',
        'type': 'object',
        'properties': {
            'id': {
                'title': 'Id',
                'type': 'integer'
            },
            'name': {
                'title': 'Name',
                'type': 'string'
            },
            'created_at': {
                'title': 'Created At',
                'description': 'The date-time the Tournament record was created at',
                'type': 'string',
                'format': 'date-time'
            }
        }
    }

Oh no! Where is the relation?

Because the models have not fully initialised, it doesn't know about the relations at this stage.

We need to initialise our model relationships early:

.. code-block:: py3

    from tortoise import Tortoise

    Tortoise.init_models(["__main__"], "models")
    # Now lets try again
    Tournament_Pydantic = pydantic_model_creator(Tournament)

The JSON-Schema of ``Tournament_Pydantic`` is now:

.. code-block:: py3

    >>> print(Tournament_Pydantic.schema())
    {
        'title': 'Tournament',
        'description': 'This references a Tournament',
        'type': 'object',
        'properties': {
            'id': {
                'title': 'Id',
                'type': 'integer'
            },
            'name': {
                'title': 'Name',
                'type': 'string'
            },
            'created_at': {
                'title': 'Created At',
                'description': 'The date-time the Tournament record was created at',
                'type': 'string',
                'format': 'date-time'
            },
            'events': {
                'title': 'Events',
                'description': 'The Tournement this happens in',
                'type': 'array',
                'items': {
                    '$ref': '#/definitions/Event'
                }
            }
        },
        'definitions': {
            'Event': {
                'title': 'Event',
                'description': 'This references an Event in a Tournament',
                'type': 'object',
                'properties': {
                    'id': {
                        'title': 'Id',
                        'type': 'integer'
                    },
                    'name': {
                        'title': 'Name',
                        'type': 'string'
                    },
                    'created_at': {
                        'title': 'Created At',
                        'type': 'string',
                        'format': 'date-time'
                    }
                }
            }
        }
    }

Aha! that's much better.

Note we can also create a model for ``Event`` the same way, and it should just work:

.. code-block:: py3

    Event_Pydantic = pydantic_model_creator(Event)

    >>> print(Event_Pydantic.schema())
    {
        'title': 'Event',
        'description': 'This references an Event in a Tournament',
        'type': 'object',
        'properties': {
            'id': {
                'title': 'Id',
                'type': 'integer'
            },
            'name': {
                'title': 'Name',
                'type': 'string'
            },
            'created_at': {
                'title': 'Created At',
                'type': 'string',
                'format': 'date-time'
            },
            'tournament': {
                'title': 'Tournament',
                'description': 'The Tournement this happens in',
                'allOf': [
                    {
                        '$ref': '#/definitions/Tournament'
                    }
                ]
            }
        },
        'definitions': {
            'Tournament': {
                'title': 'Tournament',
                'description': 'This references a Tournament',
                'type': 'object',
                'properties': {
                    'id': {
                        'title': 'Id',
                        'type': 'integer'
                    },
                    'name': {
                        'title': 'Name',
                        'type': 'string'
                    },
                    'created_at': {
                        'title': 'Created At',
                        'description': 'The date-time the Tournament record was created at',
                        'type': 'string',
                        'format': 'date-time'
                    }
                }
            }
        }
    }

And that also has the relation defined!

Lets create and serialise the objects and see what they look like *(in an async context)*:

.. code-block:: py3

    # Create objects
    tournament = await Tournament.create(name="New Tournament")
    event = await Event.create(name="The Event", tournament=tournament)

    # Serialise Tournament
    tourpy = await Tournament_Pydantic.from_tortoise_orm(tournament)

    >>> print(tourpy.json())
    {
        "id": 1,
        "name": "New Tournament",
        "created_at": "2020-03-02T07:23:27.731656",
        "events": [
            {
                "id": 1,
                "name": "The Event",
                "created_at": "2020-03-02T07:23:27.732492"
            }
        ]
    }

And serialising the event *(in an async context)*:

.. code-block:: py3

    eventpy = await Event_Pydantic.from_tortoise_orm(event)

    >>> print(eventpy.json())
    {
        "id": 1,
        "name": "The Event",
        "created_at": "2020-03-02T07:23:27.732492",
        "tournament": {
            "id": 1,
            "name": "New Tournament",
            "created_at": "2020-03-02T07:23:27.731656"
        }
    }

Creators
========

.. automodule:: tortoise.contrib.pydantic.creator
    :members:
    :exclude-members: PydanticMeta

PydanticMeta
============

.. automodule:: tortoise.contrib.pydantic.creator
    :members: PydanticMeta

Model classes
=============

.. automodule:: tortoise.contrib.pydantic.base
    :members:
