import pytest

from tortoise.contrib.test import _restore_default


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    _restore_default()


@pytest.fixture(scope="module", autouse=True)
def skip_if_codspeed_not_enabled(request):
    if not request.config.getoption("--codspeed"):
        pytest.skip("codspeed tests are disabled")
