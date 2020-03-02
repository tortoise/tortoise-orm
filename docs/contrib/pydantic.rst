.. _contrib_pydantic:

======================
Pydantic serialisation
======================

Tortoise ORM has a Pydantic plugin that will generate Pydantic Models from Tortoise Models, and then provides helper functions to serialise that model and its related objects.

We currently only support generating Pydantic objects for serialisation, and no deserialisation at this stage.

See the :ref:`examples_pydantic`

Tutorials
=========

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

Note how the class docstring and doc-comment ``#: `` is included as descriptions in the Schema.

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
