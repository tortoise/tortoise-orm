"""
Tests for __models__
"""

import os
import re
from unittest.mock import AsyncMock, patch

import pytest

from tortoise import Tortoise, connections
from tortoise.backends.base.config_generator import generate_config
from tortoise.exceptions import ConfigurationError
from tortoise.utils import get_schema_sql


async def _reset_tortoise():
    """Helper to reset Tortoise state before each test."""
    try:
        Tortoise.apps = None
        Tortoise._inited = False
    except ConfigurationError:
        pass
    Tortoise._inited = False


def _get_engine() -> str:
    """Get the current test engine."""
    db_url = os.getenv("TORTOISE_TEST_DB", "sqlite://:memory:")
    config = generate_config(db_url, app_modules={"models": []}, connection_label="models")
    return config["connections"]["models"]["engine"]


async def _init_for(module: str, safe: bool = False) -> list[str]:
    """
    Initialize Tortoise for a specific module and return SQL statements.

    Raises SkipTest if not using sqlite.
    """
    engine = _get_engine()
    if engine != "tortoise.backends.sqlite":
        pytest.skip("sqlite only")

    with patch("tortoise.backends.sqlite.client.SqliteClient.create_connection", new=AsyncMock()):
        await Tortoise.init(
            {
                "connections": {
                    "default": {
                        "engine": "tortoise.backends.sqlite",
                        "credentials": {"file_path": ":memory:"},
                    }
                },
                "apps": {"models": {"models": [module], "default_connection": "default"}},
            }
        )
        return get_schema_sql(connections.get("default"), safe).split(";\n")


def _get_sql(sqls: list[str], text: str) -> str:
    """Get SQL statement containing the given text."""
    return str(re.sub(r"[ \t\n\r]+", " ", [sql for sql in sqls if text in sql][0]))


@pytest.mark.asyncio
async def test_good():
    await _reset_tortoise()
    sqls = await _init_for("tests.model_setup.models__models__good")
    sql_joined = "; ".join(sqls)
    assert "goodtournament" in sql_joined
    assert "inaclasstournament" in sql_joined
    assert "badtournament" not in sql_joined


@pytest.mark.asyncio
async def test_bad():
    await _reset_tortoise()
    sqls = await _init_for("tests.model_setup.models__models__bad")
    sql_joined = "; ".join(sqls)
    assert "goodtournament" not in sql_joined
    assert "inaclasstournament" not in sql_joined
    assert "badtournament" in sql_joined
