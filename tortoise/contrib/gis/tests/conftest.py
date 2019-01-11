from tortoise.contrib.test import initializer, finalizer


def pytest_runtest_setup(item):
    initializer(
        ['tortoise.tests.testmodels', 'tortoise.contrib.gis.tests.testmodels'],
        db_url='sqlite://:memory:'
    )


def pytest_runtest_teardown(item, nextitem):
    finalizer()
