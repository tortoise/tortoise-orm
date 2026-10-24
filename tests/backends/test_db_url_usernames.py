import pytest

from tortoise.backends.base.config_generator import expand_db_url


@pytest.mark.parametrize("scheme", ["asyncpg", "mysql"])
@pytest.mark.parametrize(
    "encoded, expected", [("first%40last", "first@last"), ("a+b", "a+b"), ("%252F", "%2F")]
)
def test_username_is_percent_decoded_once(scheme, encoded, expected):
    config = expand_db_url(f"{scheme}://{encoded}:example@localhost/db")
    assert config["credentials"]["user"] == expected


def test_query_string_username_is_not_decoded_twice():
    config = expand_db_url("asyncpg://localhost/db?user=%252F")
    assert config["credentials"]["user"] == "%2F"
