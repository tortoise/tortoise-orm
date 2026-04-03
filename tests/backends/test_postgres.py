"""
Test some PostgreSQL-specific features
"""

import os
import ssl
import xml.etree.ElementTree as ET

import pytest
import yaml

from tests.testmodels import Tournament
from tortoise import Tortoise, connections
from tortoise.backends.base.config_generator import generate_config
from tortoise.contrib.test import requireCapability
from tortoise.exceptions import OperationalError, UnSupportedError


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


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_schema(db_isolated):
    db_config, is_asyncpg, _ = _get_db_config()

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


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_ssl_true(db_isolated):
    db_config, _, _ = _get_db_config()

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


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_ssl_custom(db_isolated):
    db_config, _, _ = _get_db_config()

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


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_application_name(db_isolated):
    db_config, is_asyncpg, is_psycopg = _get_db_config()

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


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_explain(db_simple):
    await Tournament.create(name="Test")
    result = await Tournament.all().explain()
    assert "Plan" in result[0]["QUERY PLAN"][0]


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_explain_format_text(db_simple):
    await Tournament.create(name="Test")
    result = await Tournament.all().explain(output_fmt="text")
    assert isinstance(result[0]["QUERY PLAN"], str)


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_explain_format_yaml(db_simple):
    await Tournament.create(name="Test")
    result = await Tournament.all().explain(output_fmt="yaml")
    yaml.safe_dump(result[0]["QUERY PLAN"])


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_explain_format_xml(db_simple):
    await Tournament.create(name="Test")
    result = await Tournament.all().explain(output_fmt="xml")
    ET.fromstring(result[0]["QUERY PLAN"])


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_explain_unsupported_format(db_simple):
    await Tournament.create(name="Test")
    with pytest.raises(UnSupportedError) as exc_info:
        await Tournament.all().explain(output_fmt="invalid")
    assert "Unsupported explain format" in str(exc_info.value)


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_explain_analyze(db_simple):
    await Tournament.create(name="Test")
    result = await Tournament.all().explain(analyze=True)
    assert "Plan" in result[0]["QUERY PLAN"][0]
    assert "Actual Loops" in result[0]["QUERY PLAN"][0]["Plan"]


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_explain_costs(db_simple):
    await Tournament.create(name="Test")
    result = await Tournament.all().explain(costs=True)
    assert "Plan" in result[0]["QUERY PLAN"][0]
    assert "Total Cost" in result[0]["QUERY PLAN"][0]["Plan"]


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_explain_buffers(db_simple):
    await Tournament.create(name="Test")
    result = await Tournament.all().explain(buffers=True)
    assert "Plan" in result[0]["QUERY PLAN"][0]
    assert "Shared Hit Blocks" in result[0]["QUERY PLAN"][0]["Plan"]


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_explain_timing(db_simple):
    await Tournament.create(name="Test")
    result = await Tournament.all().explain(analyze=True, timing=True)
    assert "Plan" in result[0]["QUERY PLAN"][0]
    assert "Actual Total Time" in result[0]["QUERY PLAN"][0]["Plan"]


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_explain_memory(db_simple):
    await Tournament.create(name="Test")
    result = await Tournament.all().explain(memory=True)
    assert "Plan" in result[0]["QUERY PLAN"][0]
    assert "Memory" in result[0]["QUERY PLAN"][0] or "Memory" in str(result[0]["QUERY PLAN"])


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_explain_settings(db_simple):
    await Tournament.create(name="Test")
    result = await Tournament.all().explain(settings=True)
    assert "Plan" in result[0]["QUERY PLAN"][0]


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_explain_summary(db_simple):
    await Tournament.create(name="Test")
    result = await Tournament.all().explain(summary=True)
    assert "Plan" in result[0]["QUERY PLAN"][0]
    assert "Planning Time" in result[0]["QUERY PLAN"][0]


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_explain_multiple_options(db_simple):
    await Tournament.create(name="Test")
    result = await Tournament.all().explain(analyze=True, costs=True, buffers=True)
    assert "Plan" in result[0]["QUERY PLAN"][0]
    assert "Actual Loops" in result[0]["QUERY PLAN"][0]["Plan"]
    assert "Total Cost" in result[0]["QUERY PLAN"][0]["Plan"]
    assert "Shared Hit Blocks" in result[0]["QUERY PLAN"][0]["Plan"]


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_explain_unsupported_option(db_simple):
    await Tournament.create(name="Test")
    with pytest.raises(UnSupportedError) as exc_info:
        await Tournament.all().explain(unsupported_option=True)
    assert "UNSUPPORTED_OPTION" in str(exc_info.value)


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_explain_option_false(db_simple):
    await Tournament.create(name="Test")
    result = await Tournament.all().explain(analyze=False)
    assert "Plan" in result[0]["QUERY PLAN"][0]
    assert "Actual Loops" not in str(result[0]["QUERY PLAN"])
