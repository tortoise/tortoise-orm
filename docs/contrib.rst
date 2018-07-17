=======
Contrib
=======


PyLint plugin
=============

Since Tortoise uses MetaClasses to build the Model objects, PyLint will often not understand how the Models behave. We provided a `tortoise.pylint` plugin that enhances PyLints understanding of Models and Fields.

Usage
-----

In your projects ``.pylintrc`` file, ensure the following is set:

.. code-block:: ini

    load-plugins=tortoise.contrib.pylint


UnitTest support
================

Tortoise includes its own helper utilities to assist in unit tests.

Usage
-----

.. code-block:: python3

    from tortoise.contrib import test

    class TestSomething(test.TestCase):
        def test_something(self):
            ...

        async def test_something_async(self):
            ...

        @test.skip('Skip this')
        def test_skip(self):
            ...

        @test.expectedFailure
        def test_something(self):
            ...

Reference
---------

.. automodule:: tortoise.contrib.test
    :members:
    :undoc-members:
    :show-inheritance:
