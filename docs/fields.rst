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


.. rst-class:: emphasize-children

Reference
=========

Here is the list of fields available with custom options of these fields:

Base Field
----------

.. automodule:: tortoise.fields.base
    :members:
    :undoc-members:
    :exclude-members: field_type, indexable, has_db_field, skip_to_python_if_native, allows_generated, function_cast, SQL_TYPE, GENERATED_SQL

Data Fields
-----------

.. automodule:: tortoise.fields.data
    :members:
    :exclude-members: to_db_value, to_python_value

Relational Fields
-----------------

.. automodule:: tortoise.fields.relational
    :members: ForeignKeyField, OneToOneField, ManyToManyField
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
