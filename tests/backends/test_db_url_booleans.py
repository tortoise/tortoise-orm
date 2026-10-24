import pytest

from tortoise.backends.base.config_generator import expand_db_url


@pytest.mark.parametrize(
    "url, key",
    [
        ("asyncpg://example:example@localhost/db", "ssl"),
        ("mysql://example:example@localhost/db", "use_unicode"),
        ("sqlite://:memory:", "install_regexp_functions"),
    ],
)
@pytest.mark.parametrize("value, expected", [("FALSE", False), ("0", False), ("True", True)])
def test_boolean_url_option(url, key, value, expected):
    config = expand_db_url(f"{url}?{key}={value}")
    assert config["credentials"][key] is expected
