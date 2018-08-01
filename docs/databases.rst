.. _databases:

=========
Databases
=========

Tortoise currently supports the following databases:

* PostgreSQL >= 9.4 (using ``asyncpg``)
* SQLite (using ``aiosqlite``)
* MySQL/MariaDB (using ``aiomysql``)

To use, please ensure that ``asyncpg``, ``aiosqlite`` and/or ``aiomysql`` is installed.

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

SQLite
======

.. todo::
    Document SQLite options and behaviour


PostgreSQL
==========

.. todo::
    Document PostgreSQL options and behaviour


MySQL/MariaDB
=============

.. todo::
    Document PostgreSQL options and behaviour
