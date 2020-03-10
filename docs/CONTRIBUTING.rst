==================
Contribution Guide
==================

.. toctree::
   :hidden:

   CODE_OF_CONDUCT


If you want to contribute check out issues, or just straightforwardly create PR.

Tortoise ORM is a volunteer effort. We encourage you to pitch in and join the team!

Please have a look at the :ref:`code_conduct`


Filing a bug or requesting a feature
====================================

Please check if there isn't an existing issue or pull request open that addresses your issue.
If not you are welcome to open one.

If you have an incomplete change, but won't/can't continue working on it, please create a PR in any case and mark it as ``(WIP)`` so we can help each other.


Have a chat
===========

We have a chatroom on `Gitter <https://gitter.im/tortoise/community>`_


Project structure
=================

We have a ``Makefile`` that has the common operations listed, to get started just type ``make``::

    Tortoise ORM development makefile

    usage: make <target>
    Targets:
        up          Updates dev/test dependencies
        deps        Ensure dev/test dependencies are installed
        check       Checks that build is sane
        lint        Reports all linter violations
        test        Runs all tests
        docs        Builds the documentation
        style       Auto-formats the code

So to run the tests you just need to run ``make test``, etc…

The code is structured in the following directories:

``docs/``:
    Documentation
``examples/``:
    Example code
``tortoise/``:
    Base Tortoise ORM
``tortoise/fields/``:
    The Fields are defined here.
``tortoise/backends/``:
    DB Backends, such as ``sqlite``, ``asyncpg`` & ``mysql``
``tortoise/backends/base/``:
    Common DB Backend code
``tortoise/contrib/``:
    Anything that helps people use the project, such as Testing framework and linter plugins
``tortoise/tests/``:
    The Tortoise test code


Coding Guideline
================

We believe to keep the code simple, so it is easier to test and there is less place for bugs to hide.

Priorities
----------

An important part of Tortoise ORM is that we want a simple interface, that only does what is expected.
As this is a value that is different for different people, we have settled on:

* Model/QuerySet usage should be explicit and concise.
* Keep it simple, as simple code not only often runs faster, but has less bugs too.
* Correctness > Ease-Of-Use > Performance > Maintenance
* Test everything.
* Only do performance/memory optimisation when you have a repeatable benchmark to measure with.


Style
-----

We try and automate as much as we can, so a simple ``make check`` will do automated style checking and linting, but these don't pick up on the non-obvious style preferences.

Tortoise ORM follows a the following agreed upon style:

* Keep to PEP8 where you can
* Max line-length is changed to 100
* Always try to separate out terms clearly rather than concatenate words directly:
    * ``some_purpose`` instead of ``somepurpose``
    * ``SomePurpose`` instead of ``Somepurpose``
* Keep in mind the targeted Python versions of ``>=3.7``:
    * Do use f-strings
* Please try and provide type annotations where you can, it will improve auto-completion in editors, and better static analysis.


Running tests
================
Running tests natively on windows isn't supported (yet). Best way to run them atm is by using WSL.
Postgres uses the default ``postgres`` user, mysql uses ``root``. If either of them has a password you can set it with the ``TORTOISE_POSTGRES_PASS`` and ``TORTOISE_MYSQL_PASS`` env variables respectively.



Different types of tests
-----------------------------
- ``make test``: most basic quick test. only runs the tests on in an memory sqlite database without generating a coverage report.
- ``make test_sqlite``: Runs the tests on a sqlite in memory database
- ``make test_postgres``: Runs the tests on the postgres database
- ``make test_mysql_myisam``: Runs the tests on the mysql database using the ``MYISAM`` storage engine (no transactions)
- ``make test_mysql``: Runs the tests on the mysql database
- ``make testall``: runs the tests on all 4 database types: sqlite (in memory), postgress, MySQL-MyISAM and MySQL-InnoDB
- ``green``: runs the same tests as ``make test``, ensures the green plugin works
- ``nose2 --plugin tortoise.contrib.test.nose2 --db-module tests.testmodels --db-url sqlite://:memory: ``: same test as ``make test`` , ensures the nose2 plugin works


Things to be aware of when running the test suite
---------------------------------------------------
- Some tests always run regardless of what test suite you are running (the connection tests for mysql and postgres for example, you don't need a database running as it doesn't actually connect though)
- Some tests use hardcoded databases (usually sqlite) for testing, regardless of what DB url you specified.
- The postgres driver does not work under Pypy so those tests will be skipped if you are running under pypy
- You can run only specific tests by running `` py.test <testfiles>`` or ``green -s 1 <testfile>``
- If you want a peek under the hood of test that hang to debug try running them with ``green -s 1 -vv -d -a <test>``
    - ``-s 1`` means it only runs one test at a time
    - ``-vv`` very verbose output
    - ``-d`` log debug output
    - ``-a`` don't capture stdout but just let it output
- Mysql tends to be relatively slow but there are some settings you can tweak to make it faster, however this also means less redundant. Use at own risk: http://www.tocker.ca/2013/11/04/reducing-mysql-durability-for-testing.html
