"""Test for issue #404 - expand_db_url fails with special characters in password."""

from tortoise.backends.base.config_generator import expand_db_url


def test_expand_db_url_with_brackets_in_password():
    """Test that passwords with square brackets work correctly."""
    # Password with square brackets (as mentioned in issue #404)
    db_url = "mysql://some_user:ADM[r$VIS]@test-rds.somedata.net:3306/mydb?charset=utf8mb4"

    config = expand_db_url(db_url)

    assert config["engine"] == "tortoise.backends.mysql"
    assert config["credentials"]["user"] == "some_user"
    assert config["credentials"]["password"] == "ADM[r$VIS]"
    assert config["credentials"]["host"] == "test-rds.somedata.net"
    assert config["credentials"]["port"] == 3306
    assert config["credentials"]["database"] == "mydb"
    assert config["credentials"]["charset"] == "utf8mb4"


def test_expand_db_url_with_unbalanced_brackets_in_password():
    """Test that passwords with unbalanced square brackets work correctly."""
    # Password with unbalanced bracket (causes IPv6 parsing error)
    db_url = "mysql://fail_user:DMK_15[ZWIN6@test-rds.somedata.net:3306/mydb2?charset=utf8mb4"

    config = expand_db_url(db_url)

    assert config["engine"] == "tortoise.backends.mysql"
    assert config["credentials"]["user"] == "fail_user"
    assert config["credentials"]["password"] == "DMK_15[ZWIN6"
    assert config["credentials"]["host"] == "test-rds.somedata.net"
    assert config["credentials"]["port"] == 3306
    assert config["credentials"]["database"] == "mydb2"
