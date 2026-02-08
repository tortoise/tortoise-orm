"""
Test some PostgreSQL-specific features
"""

import os
import ssl

import pytest

from tests.testmodels import Tournament
from tortoise import Tortoise, connections
from tortoise.backends.base.config_generator import generate_config
from tortoise.exceptions import OperationalError


def _get_db_config():
    """Get database config and check if it's PostgreSQL."""
    db_url = os.getenv("TORTOISE_TEST_DB", "sqlite://:memory:")
    db_config = generate_config(
        db_url,
        app_modules={"models": ["tests.testmodels"]},
        connection_label="models",
        testing=True,
    )
    engine = db_config["connections"]["models"]["engine"]
    is_asyncpg = engine == "tortoise.backends.asyncpg"
    is_psycopg = engine == "tortoise.backends.psycopg"
    return db_config, is_asyncpg, is_psycopg


@pytest.mark.asyncio
async def test_schema(db_simple):
    db_config, is_asyncpg, is_psycopg = _get_db_config()
    if not is_asyncpg and not is_psycopg:
        pytest.skip("PostgreSQL only")

    if is_asyncpg:
        from asyncpg.exceptions import InvalidSchemaNameError
    else:
        from psycopg.errors import InvalidSchemaName as InvalidSchemaNameError

    if Tortoise._inited:
        await Tortoise._drop_databases()

    try:
        db_config["connections"]["models"]["credentials"]["schema"] = "mytestschema"
        await Tortoise.init(db_config, _create_db=True)

        with pytest.raises(InvalidSchemaNameError):
            await Tortoise.generate_schemas()

        conn = connections.get("models")
        await conn.execute_script("CREATE SCHEMA mytestschema;")
        await Tortoise.generate_schemas()

        tournament = await Tournament.create(name="Test")
        await connections.close_all()

        del db_config["connections"]["models"]["credentials"]["schema"]
        await Tortoise.init(db_config)

        with pytest.raises(OperationalError):
            await Tournament.filter(name="Test").first()

        conn = connections.get("models")
        _, res = await conn.execute_query(
            "SELECT id, name FROM mytestschema.tournament WHERE name='Test' LIMIT 1"
        )

        assert len(res) == 1
        assert tournament.id == res[0]["id"]
        assert tournament.name == res[0]["name"]
    finally:
        if Tortoise._inited:
            await Tortoise._drop_databases()


@pytest.mark.asyncio
async def test_ssl_true():
    db_config, is_asyncpg, is_psycopg = _get_db_config()
    if not is_asyncpg and not is_psycopg:
        pytest.skip("PostgreSQL only")

    db_config["connections"]["models"]["credentials"]["ssl"] = True
    ssl_failed = False
    try:
        await Tortoise.init(db_config, _create_db=True)
    except (ConnectionError, ssl.SSLError):
        ssl_failed = True
    else:
        assert False, "Expected ConnectionError or SSLError"
    finally:
        # Don't try to drop database if SSL connection failed - we can't connect
        if Tortoise._inited and not ssl_failed:
            await Tortoise._drop_databases()


@pytest.mark.asyncio
async def test_ssl_custom():
    db_config, is_asyncpg, is_psycopg = _get_db_config()
    if not is_asyncpg and not is_psycopg:
        pytest.skip("PostgreSQL only")

    # Expect connectionerror or pass
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    db_config["connections"]["models"]["credentials"]["ssl"] = ssl_ctx
    ssl_failed = False
    try:
        await Tortoise.init(db_config, _create_db=True)
    except ConnectionError:
        ssl_failed = True
    finally:
        # Don't try to drop database if SSL connection failed - we can't connect
        if Tortoise._inited and not ssl_failed:
            await Tortoise._drop_databases()


@pytest.mark.asyncio
async def test_application_name():
    db_config, is_asyncpg, is_psycopg = _get_db_config()
    if not is_asyncpg and not is_psycopg:
        pytest.skip("PostgreSQL only")

    db_config["connections"]["models"]["credentials"]["application_name"] = "mytest_application"
    try:
        await Tortoise.init(db_config, _create_db=True)

        conn = connections.get("models")
        _, res = await conn.execute_query(
            "SELECT application_name FROM pg_stat_activity WHERE pid = pg_backend_pid()"
        )

        assert len(res) == 1
        assert "mytest_application" == res[0]["application_name"]
    finally:
        if Tortoise._inited:
            await Tortoise._drop_databases()
