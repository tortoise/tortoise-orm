=======
Contrib
=======


PyLint Plugin
=============

Since Tortoise uses MetaClasses to build the Model objects, PyLint will often not understand how the Models behave. We provided a `tortoise.pylint` plugin that enhances PyLints understanding of Models and Fields.

Usage
-----

In your projects ``.pylintrc`` file, ensure the following is set:

.. code-block:: ini

    load-plugins=tortoise.contrib.pylint


TestCase
========

Tortoise includes its own ``TestCase`` utility for use in testing. Currently it will create an isolated ``SQLite`` database for each and every test.

To use:

.. code-block:: python3

    from tortoise.contrib.test import TestCase

    class TestSomething(TestCase):
        async def test_something(self):
            ...
