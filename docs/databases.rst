.. _databases:

=========
Databases
=========

Tortoise currently supports the following databases:

* SQLite
* PostgreSQL >= 9.4 (using ``asyncpg``)
* MySQL/MariaDB (using ``aiomysql``)

To use, please ensure that ``asyncpg`` and/or ``aiomysql`` is installed.

.. _db_url:

DB_URL
======

Tortoise supports specifying Database configuration in a URL form.

The form is:

:samp:`{DB_TYPE}://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DB_NAME}?{PARAM1}=value&{PARAM2}=value`

If password contains special characters it need to be URL encoded:

.. code-block::  python3

    >>> import urllib.parse
    >>> urllib.parse.quote_plus("kx%jj5/g")
    'kx%25jj5%2Fg'

The supported ``DB_TYPE``:

``sqlite``:
    Typically in the form of :samp:`sqlite://{DB_FILE}`
    So if the ``DB_FILE`` is "/data/db.sqlite3" then the string will be ``sqlite:///data/db.sqlite`` (note the three /'s)
``postgres``:
    Typically in the form of :samp:`postgres://postgres:pass@db.host:5432/somedb`
``mysql``:
    Typically in the form of :samp:`mysql://myuser:mypass:pass@db.host:3306/somedb`

Capabilities
============

Since each database has a different set of features we have a ``Capabilities`` that is registered on each client.
Primarily this is to work around larger-than SQL differences, or common issues.

.. autoclass:: tortoise.backends.base.client.Capabilities
    :members:


SQLite
======

SQLite is an embedded database, and can run on a file or in-memory. Good database for local development or testing of code logic, but not recommended for production use.

.. caution::

    SQLite doesn't support many of the common datatypes natively, although we do emulation where we can, not everything is perfect.

    For example ``DecimalField`` has precision preserved by storing values as strings, except when doing aggregates/ordering on it. In those cases we have to cast to/from floating-point numbers.

    Similarily case-insensitivity is only partially implemented.

DB URL is typically in the form of :samp:`sqlite://{DB_FILE}`
So if the ``DB_FILE`` is "/data/db.sqlite3" then the string will be ``sqlite:///data/db.sqlite`` (note the three /'s)

Required Parameters
-------------------

``path``:
    Path to SQLite3 file. ``:memory:`` is a special path that indicates in-memory database.

Optional parameters:
--------------------

SQLite optional parameters is basically any of the ``PRAGMA`` statements documented `here. <https://sqlite.org/pragma.html#toc>`__

``journal_mode`` (defaults to ``WAL``):
    Specify SQLite journal mode.
``journal_size_limit`` (defaults to ``16384``):
    The journal size.
``foreign_keys``  (defaults to ``ON``)
    Set to ``OFF`` to not enforce referential integrity.


PostgreSQL
==========

DB URL is typically in the form of :samp:`postgres://postgres:pass@db.host:5432/somedb`, or, if connecting via Unix domain socket :samp:`postgres:///somedb`.

Required Parameters
-------------------

``user``:
    Username to connect with.
``password``:
    Password for username.
``host``:
    Network host that database is available at.
``port``:
    Network port that database is available at. (defaults to ``5432``)
``database``:
    Database to use.

Optional parameters:
--------------------

PostgreSQL optional parameters are pass-though parameters to the driver, see `here <https://magicstack.github.io/asyncpg/current/api/index.html#connection-pools>`__ for more details.

``minsize`` (defaults to ``1``):
    Minimum connection pool size
``maxsize`` (defaults to ``5``):
    Maximum connection pool size
``max_queries`` (defaults to ``50000``):
    Maximum no of queries before a connection is closed and replaced.
``max_inactive_connection_lifetime`` (defaults to ``300.0``):
    Duration of inactive connection before assuming that it has gone stale, and force a re-connect.
``schema`` (uses user's default schema by default):
    A specific schema to use by default.
``ssl`` (defaults to ''False``):
    Either ``True`` or a custom SSL context for self-signed certificates. See :ref:`db_ssl` for more info.

In case any of ``user``, ``password``, ``host``, ``port`` parameters is missing, we are letting ``asyncpg`` retrieve it from default sources (standard PostgreSQL environment variables or default values).


MySQL/MariaDB
=============

DB URL is typically in the form of :samp:`mysql://myuser:mypass:pass@db.host:3306/somedb`

Required Parameters
-------------------

``user``:
    Username to connect with.
``password``:
    Password for username.
``host``:
    Network host that database is available at.
``port``:
    Network port that database is available at. (defaults to ``3306``)
``database``:
    Database to use.

Optional parameters:
--------------------

MySQL optional parameters are pass-though parameters to the driver, see `here <https://aiomysql.readthedocs.io/en/latest/connection.html#connection>`__ for more details.

``minsize`` (defaults to ``1``):
    Minimum connection pool size
``maxsize`` (defaults to ``5``):
    Maximum connection pool size
``connect_timeout`` (defaults to ``None``):
    Duration to wait for connection before throwing error.
``echo`` (defaults to ``False``):
    Set to `True`` to echo SQL queries (debug only)
``no_delay`` (defaults to ``None``):
    Set to ``True`` to set TCP NO_DELAY to disable Nagle's algorithm on the socket.
``charset`` (defaults to ``utf8mb4``):
    Sets the character set in use
``ssl`` (defaults to ``False``):
    Either ``True`` or a custom SSL context for self-signed certificates. See :ref:`db_ssl` for more info.

.. _db_ssl:

Passing in custom SSL Certificates
==================================

To pass in a custom SSL Cert, one has to use the verbose init structure as the URL parser can't
handle complex objects.

.. code-block::  python3

    # Here we create a custom SSL context
    import ssl
    ctx = ssl.create_default_context()
    # And in this example we disable validation...
    # Please don't do this. Loot at the official Python ``ssl`` module documentation
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    # Here we do a verbose init
    await Tortoise.init(
        config={
            "connections": {
                "default": {
                    "engine": "tortoise.backends.asyncpg",
                    "credentials": {
                        "database": None,
                        "host": "127.0.0.1",
                        "password": "moo",
                        "port": 54321,
                        "user": "postgres",
                        "ssl": ctx  # Here we pass in the SSL context
                    }
                }
            },
            "apps": {
                "models": {
                    "models": ["some.models"],
                    "default_connection": "default",
                }
            },
        }
    )


Base DB client
==============

The Base DB client interface is provided here, but should only be directly used as an advanced case.

.. automodule:: tortoise.backends.base.client

    .. autoclass:: BaseDBAsyncClient
        :members:
        :exclude-members: query_class, executor_class, schema_generator, capabilities
