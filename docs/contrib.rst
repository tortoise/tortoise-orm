=======
Contrib
=======

.. _pylint:

PyLint plugin
=============

Since Tortoise uses MetaClasses to build the Model objects, PyLint will often not understand how the Models behave. We provided a `tortoise.pylint` plugin that enhances PyLints understanding of Models and Fields.

Usage
-----

In your projects ``.pylintrc`` file, ensure the following is set:

.. code-block:: ini

    load-plugins=tortoise.contrib.pylint


.. _unittest:

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


To get ``test.TestCase`` to work as expected, you need to configure your test environment setup and teardown to call the following:

..code-block:: python3

    from tortoise.contrib.test import initializer, finalizer

    # In setup
    initializer()

    # In teardown
    finalizer()


Furthermore, you need to set the database configuration parameter as an environment variable:

    TORTOISE_TEST_DB=sqlite:///tmp/test-{}.sqlite
    TORTOISE_TEST_DB=postgres://postgres:@127.0.0.1:54325/test_{}


The ``{}`` is a string-replacement parameter, that will create a randomised database name.
This is currently required for ``test.IsolatedTestCase`` to function.


Reference
---------

.. automodule:: tortoise.contrib.test
    :members:
    :undoc-members:
    :show-inheritance:
