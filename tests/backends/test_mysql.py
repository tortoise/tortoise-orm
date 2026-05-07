"""
Test some mysql-specific features
"""

import copy
import json
import os
import ssl

import pytest

from tests.testmodels import Tournament
from tortoise.backends.base.config_generator import generate_config
from tortoise.context import TortoiseContext
from tortoise.contrib.test import requireCapability
from tortoise.exceptions import UnSupportedError


def _get_db_config():
    """Get database config and check if it's MySQL."""
    db_url = os.getenv("TORTOISE_TEST_DB", "sqlite://:memory:")
    db_config = generate_config(
        db_url,
        app_modules={"models": ["tests.testmodels"]},
        connection_label="models",
        testing=True,
    )
    engine = db_config["connections"]["models"]["engine"]
    is_mysql = engine == "tortoise.backends.mysql"
    return db_config, is_mysql


@pytest.mark.asyncio
async def test_bad_charset():
    """Test that invalid charset raises ConnectionError."""
    base_config, is_mysql = _get_db_config()
    if not is_mysql:
        pytest.skip("MySQL only")

    # Deep copy to avoid modifying shared config
    db_config = copy.deepcopy(base_config)
    db_config["connections"]["models"]["credentials"]["charset"] = "terrible"

    async with TortoiseContext() as ctx:
        with pytest.raises(ConnectionError, match="Unknown charset"):
            await ctx.init(db_config, _create_db=True)


@pytest.mark.asyncio
async def test_ssl_true():
    """Test that SSL=True with no cert raises ConnectionError."""
    base_config, is_mysql = _get_db_config()
    if not is_mysql:
        pytest.skip("MySQL only")

    # Deep copy to avoid modifying shared config
    db_config = copy.deepcopy(base_config)
    db_config["connections"]["models"]["credentials"]["ssl"] = True
    try:
        import asyncmy  # noqa pylint: disable=unused-import

        # setting read_timeout for asyncmy. Otherwise, it will hang forever.
        db_config["connections"]["models"]["credentials"]["read_timeout"] = 1
    except ImportError:
        pass

    async with TortoiseContext() as ctx:
        with pytest.raises(ConnectionError):
            await ctx.init(db_config, _create_db=True)


@pytest.mark.asyncio
async def test_ssl_custom():
    """Test SSL with custom context (may pass or fail depending on server)."""
    base_config, is_mysql = _get_db_config()
    if not is_mysql:
        pytest.skip("MySQL only")

    # Deep copy to avoid modifying shared config
    db_config = copy.deepcopy(base_config)

    # Expect connectionerror or pass
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    db_config["connections"]["models"]["credentials"]["ssl"] = ssl_ctx

    async with TortoiseContext() as ctx:
        try:
            await ctx.init(db_config, _create_db=True)
        except ConnectionError:
            pass


@requireCapability(dialect="mysql")
@pytest.mark.asyncio
async def test_explain(db_simple):
    await Tournament.create(name="Test")
    result = await Tournament.all().explain()
    data = json.loads(result[0]["EXPLAIN"])
    assert "query_plan" in data or "query_block" in data


@requireCapability(dialect="mysql")
@pytest.mark.asyncio
async def test_explain_format_traditional(db_simple):
    await Tournament.create(name="Test")
    result = await Tournament.all().explain(output_fmt="traditional")
    assert "table" in result[0]
    assert result[0]["table"] == "tournament"


@requireCapability(dialect="mysql")
@pytest.mark.asyncio
async def test_explain_format_tree(db_simple):
    await Tournament.create(name="Test")
    result = await Tournament.all().explain(output_fmt="tree")
    assert isinstance(result[0]["EXPLAIN"], str)
    assert "->" in result[0]["EXPLAIN"]
    assert "tournament" in result[0]["EXPLAIN"]


@requireCapability(dialect="mysql")
@pytest.mark.asyncio
async def test_explain_analyze(db_simple):
    await Tournament.create(name="Test")
    # Older MySQL version don't support ANALYZE with JSON format, that's why we use TREE
    result = await Tournament.all().explain(output_fmt="tree", analyze=True)
    assert "actual" in result[0]["EXPLAIN"]


@requireCapability(dialect="mysql")
@pytest.mark.asyncio
async def test_explain_analyze_false(db_simple):
    await Tournament.create(name="Test")
    result = await Tournament.all().explain(analyze=False)
    assert "query_plan" in result[0]["EXPLAIN"] or "query_block" in result[0]["EXPLAIN"]
    assert "actual" not in result[0]["EXPLAIN"]


@requireCapability(dialect="mysql")
@pytest.mark.asyncio
async def test_explain_unsupported_format(db_simple):
    await Tournament.create(name="Test")
    with pytest.raises(UnSupportedError, match="Unsupported explain format"):
        await Tournament.all().explain(output_fmt="invalid")


@requireCapability(dialect="mysql")
@pytest.mark.asyncio
async def test_explain_unsupported_option(db_simple):
    await Tournament.create(name="Test")
    with pytest.raises(UnSupportedError, match="Unsupported options"):
        await Tournament.all().explain(unsupported_option=True)
