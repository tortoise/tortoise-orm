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

DB URL is typically in the form of :samp:`sqlite://{DB_FILE}`
So if the ``DB_FILE`` is "/data/db.sqlite3" then the string will be ``sqlite:///data/db.sqlite`` (note the three /'s)

Parameters
----------

``path``:
    Path to SQLite3 file. ``:memory:`` is a special path that indicates in-memory database.


PostgreSQL
==========

DB URL is typically in the form of :samp:`postgres://postgres:pass@db.host:5432/somedb`, or, if connecting via Unix domain socket :samp:`postgres:///somedb`.

Parameters
----------

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
``minsize``:
    Minimum connection pool size (defaults to ``1``)
``maxsize``:
    Maximum connection pool size (defaults to ``5``)
``max_queries``:
    Maximum no of queries before a connection is closed and replaced. (defaults to ``50000``)
``max_inactive_connection_lifetime``:
    Duration of inactive connection before assuming that it has gone stale, and force a re-connect.
``schema``:
    A specific schema to use by default.

In case any of ``user``, ``password``, ``host``, ``port`` parameters is missing, we are letting ``asyncpg`` retrieve it from default sources (standard PostgreSQL environment variables or default values).


MySQL/MariaDB
=============

DB URL is typically in the form of :samp:`mysql://myuser:mypass:pass@db.host:3306/somedb`

Parameters
----------

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
``minsize``:
    Minimum connection pool size (defaults to ``1``)
``maxsize``:
    Maximum connection pool size (defaults to ``5``)
``connect_timeout``:
    Duration to wait for connection before throwing error.
``echo``:
    Echo SQL queries (debug only)
``no_delay``:
    Sets TCP NO_DELAY to disable Nagle.
``charset``:
    Sets the character set in use, defaults to ``utf8mb4``


Reference
=========

.. automodule:: tortoise.backends.base.client
    :members:
    :undoc-members:
