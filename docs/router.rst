.. _router:

======
Router
======

The easiest way to use multiple databases is to set up a database routing scheme. The default routing scheme ensures that objects remain 'sticky' to their original database (i.e., an object retrieved from the foo database will be saved to the same database). The default routing scheme also ensures that if a database isn't specified, all queries fall back to the default database.

Usage
=====

Define Router
-------------

Defining a router is simple - you just need to write a class that has `db_for_read` and `db_for_write` methods.

.. code-block:: python3

    class Router:
        def db_for_read(self, model: Type[Model]):
            return "slave"

        def db_for_write(self, model: Type[Model]):
            return "master"

Both methods return a connection identifier that must be defined in the Tortoise configuration.

Configure Router
----------------

Simply include the router in your Tortoise configuration or pass it to the `Tortoise.init` method.

.. code-block:: python3

    CONFIG = {
        "connections": {
            "master": "sqlite:///tmp/m.db",
            "slave": "sqlite:///tmp/s.db",
        },
        "apps": {
            "app": {
                "models": ["__main__"],
                "default_connection": "master",
            }
        },
        "routers": ["path.Router"],
        "use_tz": False,
        "timezone": "UTC",
    }
    await Tortoise.init(config=CONFIG)


With this configuration, all `select` operations will use the `slave` connection, while all `create/update/delete` operations will use the `master` connection.
