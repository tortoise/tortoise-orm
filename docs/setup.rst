======
Set up
======

.. _init_app:

Initialize Your Application
===========================

After defining all your models, Tortoise ORM requires initialization to create backward relations between models and match your database client with the appropriate models.

You can initialize your application like this:

.. code-block:: python3

    from tortoise import Tortoise

    async def init():
        # Here we create a SQLite DB using file "db.sqlite3"
        # and specify the app name "models"
        # which contains models from "app.models"
        await Tortoise.init(
            db_url='sqlite://db.sqlite3',
            modules={'app': ['app.models']}
        )
        # Generate the schema
        await Tortoise.generate_schemas()


This example creates a connection to a SQLite database client and then discovers and initializes your models. The example configures the ``app`` application to load models from the ``app.models`` module. In this example it is a single application, but you can use multiple applications to group models.

The ``generate_schemas()`` method generates the database schema on an empty database. When generating schemas, you can set the ``safe`` parameter to ``True``, which will only create tables if they don't already exist:

.. code-block:: python3

    await Tortoise.generate_schemas(safe=True)

See :ref:`migration` for schema migration tools.

If you define a ``__models__`` variable in your ``app.models`` module (or wherever you specify to load your models from), ``generate_schemas()`` will use that list instead of automatically discovering models.

Another way of initializing the application is to use the ``Tortoise.init()`` method with the ``config`` parameter.

.. code-block:: python3

    CONFIG = {
        "connections": {
            "default": {
                "engine": "tortoise.backends.sqlite",
                "credentials": {"file_path": "default.sqlite3"},
            },
            "another_conn": {
                "engine": "tortoise.backends.sqlite",
                "credentials": {"file_path": "another_conn.sqlite3"},
            },
        },
        "apps": {
            "app": {"models": ["app.models"], "default_connection": "default"},
            "another_app": {"models": ["another_app.models"], "default_connection": "another_conn"},
        },
    }

    await Tortoise.init(config=CONFIG)


This way of initializing the application is useful when you want to configure different databases for different applications. This also allows to configure connection routing, see :ref:`router` for more details. Also check out :ref:`contrib_fastapi`, :ref:`contrib_sanic` and documentation on other integrations.

.. _cleaningup:

The Importance of Cleaning Up
=================================

Tortoise ORM maintains open connections to external databases. As an ``asyncio``-based Python library, these connections must be closed properly, or the Python interpreter may continue waiting for their completion.

To ensure connections are properly closed, make sure to call ``Tortoise.close_connections()``:

.. code-block:: python3

    await Tortoise.close_connections()

The helper function ``tortoise.run_async()`` automatically ensures that connections are closed when your application terminates.

.. _global_fallback:

Global Context Fallback
=======================

By default, Tortoise ORM uses Python's ``contextvars`` to track the active context. This works
well when ``Tortoise.init()`` is called from the same task that will execute queries.

However, in some scenarios, initialization happens in a **different task** than where queries
run. For example:

- ASGI lifespan handlers that run in a background task
- Framework setup code that spawns a separate initialization task
- Test harnesses that manage app lifecycle in background tasks

In these cases, the context set in the initialization task is not visible to other tasks,
resulting in ``RuntimeError: No TortoiseContext is currently active``.

To solve this, use the ``_enable_global_fallback`` parameter:

.. code-block:: python3

    await Tortoise.init(
        db_url='sqlite://db.sqlite3',
        modules={'models': ['app.models']},
        _enable_global_fallback=True,
    )

When enabled, the context is stored in a global variable in addition to the contextvar,
making it accessible from any task in the process.

**Important considerations:**

- Only **one** global fallback context can be active at a time
- Attempting to enable global fallback when one is already set raises ``ConfigurationError``
- For multiple isolated contexts, use explicit ``TortoiseContext()`` instances instead
- The global fallback is automatically cleared when ``Tortoise.close_connections()`` is called

This parameter is also available in ``TortoiseContext.init()`` and framework integrations
like ``RegisterTortoise`` (where it defaults to ``True``).
