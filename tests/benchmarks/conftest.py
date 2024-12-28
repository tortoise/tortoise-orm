import pytest

from tortoise.contrib.test import _restore_default


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    _restore_default()
