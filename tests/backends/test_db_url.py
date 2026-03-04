import pytest

from tortoise.backends.base.config_generator import expand_db_url, generate_config
from tortoise.exceptions import ConfigurationError

# These are pure logic tests - no database fixture needed

_postgres_scheme_engines = {
    "postgres": "tortoise.backends.asyncpg",
    "asyncpg": "tortoise.backends.asyncpg",
    "psycopg": "tortoise.backends.psycopg",
}


def test_unknown_scheme():
    with pytest.raises(ConfigurationError):
        expand_db_url("moo://baa")


def test_sqlite_basic():
    res = expand_db_url("sqlite:///some/test.sqlite")
    assert res == {
        "engine": "tortoise.backends.sqlite",
        "credentials": {
            "file_path": "/some/test.sqlite",
            "journal_mode": "WAL",
            "journal_size_limit": 16384,
        },
    }


def test_sqlite_no_db():
    with pytest.raises(ConfigurationError, match="No path specified for DB_URL"):
        expand_db_url("sqlite://")


def test_sqlite_relative():
    res = expand_db_url("sqlite://test.sqlite")
    assert res == {
        "engine": "tortoise.backends.sqlite",
        "credentials": {
            "file_path": "test.sqlite",
            "journal_mode": "WAL",
            "journal_size_limit": 16384,
        },
    }


def test_sqlite_relative_with_subdir():
    res = expand_db_url("sqlite://data/db.sqlite")
    assert res == {
        "engine": "tortoise.backends.sqlite",
        "credentials": {
            "file_path": "data/db.sqlite",
            "journal_mode": "WAL",
            "journal_size_limit": 16384,
        },
    }


def test_sqlite_testing():
    res = expand_db_url(db_url="sqlite:///some/test-{}.sqlite", testing=True)
    file_path = res["credentials"]["file_path"]
    assert "/some/test-" in file_path
    assert ".sqlite" in file_path
    assert "sqlite:///some/test-{}.sqlite" != file_path
    assert res == {
        "engine": "tortoise.backends.sqlite",
        "credentials": {
            "file_path": file_path,
            "journal_mode": "WAL",
            "journal_size_limit": 16384,
        },
    }


def test_sqlite_params():
    res = expand_db_url("sqlite:///some/test.sqlite?AHA=5&moo=yes&journal_mode=TRUNCATE")
    assert res == {
        "engine": "tortoise.backends.sqlite",
        "credentials": {
            "file_path": "/some/test.sqlite",
            "AHA": "5",
            "moo": "yes",
            "journal_mode": "TRUNCATE",
            "journal_size_limit": 16384,
        },
    }


def test_sqlite_invalid():
    with pytest.raises(ConfigurationError):
        expand_db_url("sqlite://")


def test_postgres_basic():
    for scheme, engine in _postgres_scheme_engines.items():
        res = expand_db_url(f"{scheme}://postgres:moo@127.0.0.1:54321/test")
        assert res == {
            "engine": engine,
            "credentials": {
                "database": "test",
                "host": "127.0.0.1",
                "password": "moo",
                "port": 54321,
                "user": "postgres",
            },
        }


def test_postgres_encoded_password():
    for scheme, engine in _postgres_scheme_engines.items():
        res = expand_db_url(f"{scheme}://postgres:kx%25jj5%2Fg@127.0.0.1:54321/test")
        assert res == {
            "engine": engine,
            "credentials": {
                "database": "test",
                "host": "127.0.0.1",
                "password": "kx%jj5/g",
                "port": 54321,
                "user": "postgres",
            },
        }


def test_postgres_no_db():
    for scheme, engine in _postgres_scheme_engines.items():
        res = expand_db_url(f"{scheme}://postgres:moo@127.0.0.1:54321")
        assert res == {
            "engine": engine,
            "credentials": {
                "database": None,
                "host": "127.0.0.1",
                "password": "moo",
                "port": 54321,
                "user": "postgres",
            },
        }


def test_postgres_no_port():
    for scheme, engine in _postgres_scheme_engines.items():
        res = expand_db_url(f"{scheme}://postgres@127.0.0.1/test")
        assert res == {
            "engine": engine,
            "credentials": {
                "database": "test",
                "host": "127.0.0.1",
                "password": None,
                "port": 5432,
                "user": "postgres",
            },
        }


def test_postgres_nonint_port():
    for scheme in _postgres_scheme_engines:
        with pytest.raises(ConfigurationError):
            expand_db_url(f"{scheme}://postgres:@127.0.0.1:moo/test")


def test_postgres_testing():
    for scheme, engine in _postgres_scheme_engines.items():
        res = expand_db_url(
            db_url=(f"{scheme}://postgres@127.0.0.1:5432/" + r"test_\{\}"), testing=True
        )
        database = res["credentials"]["database"]
        assert "test_" in database
        assert "test_{}" != database
        assert res == {
            "engine": engine,
            "credentials": {
                "database": database,
                "host": "127.0.0.1",
                "password": None,
                "port": 5432,
                "user": "postgres",
            },
        }


def test_postgres_params():
    for scheme, engine in _postgres_scheme_engines.items():
        res = expand_db_url(f"{scheme}://postgres@127.0.0.1:5432/test?AHA=5&moo=yes")
        assert res == {
            "engine": engine,
            "credentials": {
                "database": "test",
                "host": "127.0.0.1",
                "password": None,
                "port": 5432,
                "user": "postgres",
                "AHA": "5",
                "moo": "yes",
            },
        }


def test_mysql_special_chars_in_password():
    db_url = "mysql://some_user:ADM[r$VIS]@test-rds.somedata.net:3306/mydb?charset=utf8mb4"
    res = expand_db_url(db_url)
    assert res == {
        "engine": "tortoise.backends.mysql",
        "credentials": {
            "database": "mydb",
            "host": "test-rds.somedata.net",
            "password": "ADM[r$VIS]",
            "port": 3306,
            "user": "some_user",
            "charset": "utf8mb4",
            "sql_mode": "STRICT_TRANS_TABLES",
        },
    }


def test_mysql_unbalanced_brackets_in_password():
    db_url = "mysql://fail_user:DMK_15[ZWIN6@test-rds.somedata.net:3306/mydb2?charset=utf8mb4"
    res = expand_db_url(db_url)
    assert res == {
        "engine": "tortoise.backends.mysql",
        "credentials": {
            "database": "mydb2",
            "host": "test-rds.somedata.net",
            "password": "DMK_15[ZWIN6",
            "port": 3306,
            "user": "fail_user",
            "charset": "utf8mb4",
            "sql_mode": "STRICT_TRANS_TABLES",
        },
    }


def test_mysql_literal_percent_in_password_is_corrupted():
    # Known limitation: a literal '%' followed by valid hex (e.g. '%ba') gets
    # decoded by unquote_plus, corrupting the password. Users must pre-encode
    # '%' as '%25' in their URLs to avoid this.
    db_url = "mysql://user:foo%bar@127.0.0.1:3306/mydb"
    res = expand_db_url(db_url)
    assert res["credentials"]["password"] != "foo%bar"


def test_mysql_pre_encoded_percent_in_password():
    db_url = "mysql://user:foo%25bar@127.0.0.1:3306/mydb"
    res = expand_db_url(db_url)
    assert res["credentials"]["password"] == "foo%bar"


def test_postgres_plus_sign_in_password():
    for scheme, engine in _postgres_scheme_engines.items():
        res = expand_db_url(f"{scheme}://postgres:p%2Bss+word@127.0.0.1:54321/test")
        assert res["credentials"]["password"] == "p+ss+word"


def test_mysql_basic():
    res = expand_db_url("mysql://root:@127.0.0.1:33060/test")
    assert res == {
        "engine": "tortoise.backends.mysql",
        "credentials": {
            "database": "test",
            "host": "127.0.0.1",
            "password": "",
            "port": 33060,
            "user": "root",
            "charset": "utf8mb4",
            "sql_mode": "STRICT_TRANS_TABLES",
        },
    }


def test_mysql_encoded_password():
    res = expand_db_url("mysql://root:kx%25jj5%2Fg@127.0.0.1:33060/test")
    assert res == {
        "engine": "tortoise.backends.mysql",
        "credentials": {
            "database": "test",
            "host": "127.0.0.1",
            "password": "kx%jj5/g",
            "port": 33060,
            "user": "root",
            "charset": "utf8mb4",
            "sql_mode": "STRICT_TRANS_TABLES",
        },
    }


def test_mysql_no_db():
    res = expand_db_url("mysql://root:@127.0.0.1:33060")
    assert res == {
        "engine": "tortoise.backends.mysql",
        "credentials": {
            "database": None,
            "host": "127.0.0.1",
            "password": "",
            "port": 33060,
            "user": "root",
            "charset": "utf8mb4",
            "sql_mode": "STRICT_TRANS_TABLES",
        },
    }


def test_mysql_no_port():
    res = expand_db_url("mysql://root@127.0.0.1/test")
    assert res == {
        "engine": "tortoise.backends.mysql",
        "credentials": {
            "database": "test",
            "host": "127.0.0.1",
            "password": "",
            "port": 3306,
            "user": "root",
            "charset": "utf8mb4",
            "sql_mode": "STRICT_TRANS_TABLES",
        },
    }


def test_mysql_nonint_port():
    with pytest.raises(ConfigurationError):
        expand_db_url("mysql://root:@127.0.0.1:moo/test")


def test_mysql_testing():
    res = expand_db_url(r"mysql://root:@127.0.0.1:3306/test_\{\}", testing=True)
    assert "test_" in res["credentials"]["database"]
    assert "test_{}" != res["credentials"]["database"]
    assert res == {
        "engine": "tortoise.backends.mysql",
        "credentials": {
            "database": res["credentials"]["database"],
            "host": "127.0.0.1",
            "password": "",
            "port": 3306,
            "user": "root",
            "charset": "utf8mb4",
            "sql_mode": "STRICT_TRANS_TABLES",
        },
    }


def test_mysql_params():
    res = expand_db_url(
        "mysql://root:@127.0.0.1:3306/test?AHA=5&moo=yes&maxsize=20&minsize=5"
        "&connect_timeout=1.5&echo=1&ssl=True"
    )
    assert res == {
        "engine": "tortoise.backends.mysql",
        "credentials": {
            "database": "test",
            "host": "127.0.0.1",
            "password": "",
            "port": 3306,
            "user": "root",
            "AHA": "5",
            "moo": "yes",
            "minsize": 5,
            "maxsize": 20,
            "connect_timeout": 1.5,
            "echo": True,
            "charset": "utf8mb4",
            "sql_mode": "STRICT_TRANS_TABLES",
            "ssl": True,
        },
    }


def test_generate_config_basic():
    res = generate_config(
        db_url="sqlite:///some/test.sqlite",
        app_modules={"models": ["one.models", "two.models"]},
    )
    assert res == {
        "connections": {
            "default": {
                "credentials": {
                    "file_path": "/some/test.sqlite",
                    "journal_mode": "WAL",
                    "journal_size_limit": 16384,
                },
                "engine": "tortoise.backends.sqlite",
            }
        },
        "apps": {
            "models": {
                "models": ["one.models", "two.models"],
                "default_connection": "default",
            }
        },
    }


def test_generate_config_explicit():
    res = generate_config(
        db_url="sqlite:///some/test.sqlite",
        app_modules={"models": ["one.models", "two.models"]},
        connection_label="models",
        testing=True,
    )
    assert res == {
        "connections": {
            "models": {
                "credentials": {
                    "file_path": "/some/test.sqlite",
                    "journal_mode": "WAL",
                    "journal_size_limit": 16384,
                },
                "engine": "tortoise.backends.sqlite",
            }
        },
        "apps": {
            "models": {
                "models": ["one.models", "two.models"],
                "default_connection": "models",
            }
        },
    }


def test_generate_config_many_apps():
    res = generate_config(
        db_url="sqlite:///some/test.sqlite",
        app_modules={"models": ["one.models", "two.models"], "peanuts": ["peanut.models"]},
    )
    assert res == {
        "connections": {
            "default": {
                "credentials": {
                    "file_path": "/some/test.sqlite",
                    "journal_mode": "WAL",
                    "journal_size_limit": 16384,
                },
                "engine": "tortoise.backends.sqlite",
            }
        },
        "apps": {
            "models": {
                "models": ["one.models", "two.models"],
                "default_connection": "default",
            },
            "peanuts": {"models": ["peanut.models"], "default_connection": "default"},
        },
    }
