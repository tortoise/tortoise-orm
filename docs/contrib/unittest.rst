.. _unittest:

================
UnitTest support
================

Tortoise ORM includes its own helper utilities to assist in unit tests.

Usage
=====

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

.. code-block:: python3

    from tortoise.contrib.test import initializer, finalizer

    # In setup
    initializer(['module.a', 'module.b.c'])
    # With optional db_url, app_label and loop parameters
    initializer(['module.a', 'module.b.c'], db_url='...', app_label="someapp", loop=loop)
    # Or env-var driven → See Green test runner section below.
    env_initializer()

    # In teardown
    finalizer()


On the DB_URL it should follow the following standard:

    TORTOISE_TEST_DB=sqlite:///tmp/test-{}.sqlite
    TORTOISE_TEST_DB=postgres://postgres:@127.0.0.1:5432/test_{}


The ``{}`` is a string-replacement parameter, that will create a randomized database name.
This is currently required for ``test.IsolatedTestCase`` to function.
If you don't use ``test.IsolatedTestCase`` then you can give an absolute address.
The SQLite in-memory ``:memory:`` database will always work, and is the default.

.. rst-class:: emphasize-children

Test Runners
============

Green
-----

In your ``.green`` file:

.. code-block:: ini

    initializer = tortoise.contrib.test.env_initializer
    finalizer = tortoise.contrib.test.finalizer

And then define the ``TORTOISE_TEST_MODULES`` environment variable with a comma separated list of module paths.

Furthermore, you may set the database configuration parameter as an environment variable (defaults to ``sqlite://:memory:``):

    TORTOISE_TEST_DB=sqlite:///tmp/test-{}.sqlite
    TORTOISE_TEST_DB=postgres://postgres:@127.0.0.1:5432/test_{}


Py.test
-------

.. note::

    pytest 5.4.0 & 5.4.1 has a bug that stops it from working with async test cases. You may have to install ``pytest>=5.4.2`` to get it to work.

Run the initializer and finalizer in your ``conftest.py`` file:

.. code-block:: python3

    import os
    import pytest
    from tortoise.contrib.test import finalizer, initializer

    @pytest.fixture(scope="session", autouse=True)
    def initialize_tests(request):
        db_url = os.environ.get("TORTOISE_TEST_DB", "sqlite://:memory:")
        initializer(["tests.testmodels"], db_url=db_url, app_label="models")
        request.addfinalizer(finalizer)


Pytest-asyncio
--------------

For users of ``pytest-asyncio``, Tortoise ORM provides the ``create_db`` async function
that can be used directly in async fixtures. This is the recommended approach for
pytest-asyncio users as it provides more flexibility.

Basic usage with ``create_db``:

.. code-block:: python3

    import pytest
    import pytest_asyncio
    from tortoise import Tortoise
    from tortoise.contrib.test import create_db

    @pytest_asyncio.fixture
    async def db():
        await create_db(["myapp.models"], db_url="sqlite://:memory:", app_label="models")
        yield
        await Tortoise._drop_databases()

    @pytest.mark.asyncio
    async def test_something(db):
        from myapp.models import MyModel
        # Database is ready to use
        item = await MyModel.create(name="test")
        assert item.id is not None

You can also pre-populate the database with test data in the fixture:

.. code-block:: python3

    import pytest
    import pytest_asyncio
    from tortoise import Tortoise
    from tortoise.contrib.test import create_db

    @pytest_asyncio.fixture
    async def db_with_data():
        await create_db(["myapp.models"], db_url="sqlite://:memory:", app_label="models")

        # Pre-populate with test data
        from myapp.models import User
        await User.create(username="admin", email="admin@example.com")
        await User.create(username="user1", email="user1@example.com")

        yield

        await Tortoise._drop_databases()

    @pytest.mark.asyncio
    async def test_users_exist(db_with_data):
        from myapp.models import User
        users = await User.all()
        assert len(users) == 2

See the ``examples/pytest`` directory for a complete example project.


Nose2
-----

Load the plugin ``tortoise.contrib.test.nose2`` either via command line::

    nose2 --plugin tortoise.contrib.test.nose2 --db-module tortoise.tests.testmodels

Or via the config file:

.. code-block:: ini

    [unittest]
    plugins = tortoise.contrib.test.nose2

    [tortoise]
    # Must specify at least one module path
    db-module =
        tests.testmodels
    # You can optionally override the db_url here
    db-url = sqlite://testdb-{}.sqlite


Reference
=========

.. automodule:: tortoise.contrib.test
    :members:
    :undoc-members:
    :show-inheritance:
