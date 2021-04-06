.. _router:

======
Router
======

The easiest way to use multiple databases is to set up a database routing scheme. The default routing scheme ensures that objects remain 'sticky' to their original database (i.e., an object retrieved from the foo database will be saved on the same database). The default routing scheme ensures that if a database isn't specified, all queries fall back to the default database.

Usage
=====

Define Router
-------------

Define a router is simple, you need just write a class that has `db_for_read` and `db_for_write` methods.

.. code-block:: python3

    class Router:
        def db_for_read(self, model: Type[Model]):
            return "slave"

        def db_for_write(self, model: Type[Model]):
            return "master"

The two methods return a connection string defined in configuration.

Config Router
-------------

Just put it in configuration of tortoise or in `Tortoise.init` method.

.. code-block:: python3

    config = {
        "connections": {"master": "sqlite:///tmp/test.db", "slave": "sqlite:///tmp/test.db"},
        "apps": {
            "models": {
                "models": ["__main__"],
                "default_connection": "master",
            }
        },
        "routers": ["path.Router"],
        "use_tz": False,
        "timezone": "UTC",
    }
    await Tortoise.init(config=config)
    # or
    routers = config.pop('routers')
    await Tortoise.init(config=config, routers=routers)

After that, all `select` operations will use `slave` connection, all `create/update/delete` operations will use `master` connection.
