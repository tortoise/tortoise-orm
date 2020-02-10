.. _schema:

===============
Schema Creation
===============

Here we create connection to SQLite database client and then we discover & initialize models.

.. automethod:: tortoise.Tortoise.generate_schemas
    :noindex:

``generate_schema`` generates schema on empty database.
There is also the default option when generating the schemas to set the ``safe`` parameter to ``True`` which will only insert the tables if they don't already exist.


Helper Functions
================

.. automodule:: tortoise.utils
    :members: get_schema_sql, generate_schema_for_client
