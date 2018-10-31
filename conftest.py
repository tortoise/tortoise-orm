from tortoise.contrib.test import finalizer, initializer


def pytest_runtest_setup(item):
    initializer(['tortoise.tests.testmodels'], db_url='sqlite://:memory:')


def pytest_runtest_teardown(item, nextitem):
    finalizer()
