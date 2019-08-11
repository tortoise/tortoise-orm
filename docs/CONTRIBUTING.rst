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
* Test everything. (Currently our test suite is not yet mature)
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
* Keep in mind the targeted Python versions of ``>=3.5.3``:
    * Don't use f-strings
    * Stick to comment-style variable type annotations
* Please try and provide type annotations where you can, it will improve auto-completion in editors, and better static analysis.


