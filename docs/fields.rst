.. _fields:

======
Fields
======


Usage
=====

Fields are defined as properties of a ``Model`` class object:

.. code-block:: python3

    from tortoise.models import Model
    from tortoise import fields

    class Tournament(Model):
        id = fields.IntField(pk=True)
        name = fields.CharField(max_length=255)


Reference
=========

Common parameters for fields:

``source_field`` (str):
    Name of the field in the database schema. Defaults to ``None``, which makes
    Tortoise use the same name as the attribute the field is assigned to.
``null`` (bool):
    Whether the field is nullable. Defaults to ``False``.
``default`` (value or callable):
    A default value for the field. This can also be a callable for lazy or mutable defaults.
    Defaults to ``None``, which has no effect unless the field is nullable.
``unique`` (bool):
    Require that values for the field are unique. Defaults to ``False``.
``index`` (bool):
    Set to ``True`` to create a B-Tree index for this field.
``generated`` (bool):
    A flag indicating that this field is read-only and its value is generated in database.
    You typically don't need to use this if you created the schema through Tortoise.
    Defaults to ``False``.
``description`` (str):
    Human readable description of the field. Defaults to ``None``. This allows consumers 
    to build automated documentation tooling based on the declarative model api. This field is also
    leveraged to generate comment messages for each database columns.

Read-only properties:

``required`` (bool):
    An indicator of whether a value should be provided for this field when
    building model instances. For reference, this is only ``True`` if the field
    has no default value, is not nullable and is not generated.

Here is the list of fields available at the moment with custom options of these fields:

Base Field
----------

.. autoclass:: tortoise.fields.Field
    :members:
    :undoc-members:

Data Fields
-----------

.. autoclass:: tortoise.fields.IntField
    :exclude-members: to_db_value, to_python_value

.. autoclass:: tortoise.fields.BigIntField
    :exclude-members: to_db_value, to_python_value

.. autoclass:: tortoise.fields.SmallIntField
    :exclude-members: to_db_value, to_python_value

.. autoclass:: tortoise.fields.CharField
    :exclude-members: to_db_value, to_python_value

.. autoclass:: tortoise.fields.TextField
    :exclude-members: to_db_value, to_python_value

.. autoclass:: tortoise.fields.BooleanField
    :exclude-members: to_db_value, to_python_value

.. autoclass:: tortoise.fields.DecimalField
    :exclude-members: to_db_value, to_python_value

.. autoclass:: tortoise.fields.DatetimeField
    :exclude-members: to_db_value, to_python_value

.. autoclass:: tortoise.fields.DateField
    :exclude-members: to_db_value, to_python_value

.. autoclass:: tortoise.fields.TimeDeltaField
    :exclude-members: to_db_value, to_python_value

.. autoclass:: tortoise.fields.FloatField
    :exclude-members: to_db_value, to_python_value

.. autoclass:: tortoise.fields.JSONField
    :exclude-members: to_db_value, to_python_value

.. autoclass:: tortoise.fields.UUIDField
    :exclude-members: to_db_value, to_python_value

ForeignKeyField
---------------

.. autoclass:: tortoise.fields.ForeignKeyField
    :exclude-members: to_db_value, to_python_value


ManyToManyField
---------------

.. autoclass:: tortoise.fields.ManyToManyField
    :exclude-members: to_db_value, to_python_value


Extending A Field
=================

It is possible to subclass fields allowing use of arbitrary types as long as they can be represented in a
database compatible format. An example of this would be a simple wrapper around the :class:`~tortoise.fields.CharField`
to store and query Enum types.

.. code-block:: python3

    from enum import Enum
    from typing import Type

    from tortoise import ConfigurationError
    from tortoise.fields import CharField


    class EnumField(CharField):
        """
        An example extension to CharField that serializes Enums
        to and from a str representation in the DB.
        """

        def __init__(self, enum_type: Type[Enum], **kwargs):
            super().__init__(128, **kwargs)
            if not issubclass(enum_type, Enum):
                raise ConfigurationError("{} is not a subclass of Enum!".format(enum_type))
            self._enum_type = enum_type

        def to_db_value(self, value: Enum, instance) -> str:
            return value.value

        def to_python_value(self, value: str) -> Enum:
            try:
                return self._enum_type(value)
            except Exception:
                raise ValueError(
                    "Database value {} does not exist on Enum {}.".format(value, self._enum_type)
                )

When subclassing, make sure that the ``to_db_value`` returns the same type as the superclass (in the case of CharField,
that is a ``str``) and that, naturally, ``to_python_value`` accepts the same type in the value parameter (also ``str``).
