import pytest


@pytest.fixture(scope="session", autouse=True)
def initialize_tests():
    return None
