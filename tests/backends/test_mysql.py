"""
Test some mysql-specific features
"""

import copy
import os
import ssl

import pytest

from tortoise.backends.base.config_generator import generate_config
from tortoise.context import TortoiseContext


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
