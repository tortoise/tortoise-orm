import os

import pytest

from tortoise.contrib.test import finalizer, initializer


@pytest.fixture(scope="session", autouse=True)
def initialize_tests(request):
    # Reduce the default timeout for psycopg because the tests become very slow otherwise
    try:
        from tortoise.backends.psycopg import PsycopgClient

        PsycopgClient.default_timeout = float(os.environ.get("TORTOISE_POSTGRES_TIMEOUT", "15"))
    except ImportError:
        pass

    db_url = os.getenv("TORTOISE_TEST_DB", "sqlite://:memory:")
    initializer(["tests.testmodels"], db_url=db_url)
    request.addfinalizer(finalizer)
