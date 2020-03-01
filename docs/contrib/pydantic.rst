.. _contrib_pydantic:

======================
Pydantic serialisation
======================

Tortoise ORM has a Pydantic plugin that will generate Pydantic Models from Tortoise Models, and then provides helper functions to serialise that model and its related objects.

We currently only support generating Pydantic objects for serialisation, and no deserialisation at this stage.

See the :ref:`examples_pydantic`

Tutorial 1
==========

Lets start with a basic Tortoise Model:

.. code-block:: py3

    from tortoise import fields
    from tortoise.models import Model

    class Tournament(Model):
        id = fields.IntField(pk=True)
        name = fields.TextField()
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

Tutorial 1 source
-----------------
.. literalinclude::  ../../examples/pydantic/tutorial_1.py


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
