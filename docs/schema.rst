.. _schema:

===============
Schema Creation
===============

Here we create connection to SQLite database client and then we discover & initialize models.

.. automethod:: tortoise.Tortoise.generate_schemas
    :noindex:

``generate_schema`` generates schema on empty database.
There is also the default option when generating the schemas to set the ``safe`` parameter to ``True`` which will only insert the tables if they don't already exist.

Non-default Database Schemas
============================

Tortoise ORM supports placing tables in non-default database schemas on PostgreSQL and MSSQL
(on MySQL, ``schema`` maps to a separate database name via `` `db`.`table` `` syntax).
Set the ``schema`` attribute in a model's ``Meta`` class:

.. code-block:: python3

    class Product(Model):
        name = fields.CharField(max_length=200)

        class Meta:
            schema = "catalog"

    class Inventory(Model):
        product = fields.ForeignKeyField("models.Product")
        quantity = fields.IntField()

        class Meta:
            schema = "warehouse"

Cross-schema foreign keys work automatically. The migration framework also handles schema-qualified
tables, including schema creation when needed.

Helper Functions
================

.. automodule:: tortoise.utils
    :members: get_schema_sql, generate_schema_for_client
