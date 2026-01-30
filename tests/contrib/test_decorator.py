import os
import subprocess  # nosec
import sys
from unittest.mock import AsyncMock, patch

import pytest

from tortoise.contrib.test import init_memory_sqlite, requireCapability


@pytest.mark.asyncio
@requireCapability(dialect="sqlite")
async def test_basic_example_script(db) -> None:
    """Test that the basic example script runs successfully."""
    # Set PYTHONPATH to use local source instead of installed package
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    r = subprocess.run(  # nosec
        [sys.executable, "examples/basic.py"], capture_output=True, text=True, env=env
    )
    assert not r.stderr, f"Script had errors: {r.stderr}"
    output = r.stdout
    s = "[{'id': 1, 'name': 'Updated name'}, {'id': 2, 'name': 'Test 2'}]"
    assert s in output


@pytest.mark.asyncio
@requireCapability(dialect="sqlite")
@patch("tortoise.Tortoise.init")
@patch("tortoise.Tortoise.generate_schemas")
async def test_init_memory_sqlite_decorator(
    mocked_generate: AsyncMock,
    mocked_init: AsyncMock,
    db,
) -> None:
    """Test init_memory_sqlite as decorator without parentheses."""

    @init_memory_sqlite
    async def run():
        return "result"

    result = await run()
    assert result == "result"
    mocked_init.assert_awaited_once_with(
        db_url="sqlite://:memory:", modules={"models": ["__main__"]}
    )
    mocked_generate.assert_awaited_once()


@pytest.mark.asyncio
@requireCapability(dialect="sqlite")
@patch("tortoise.Tortoise.init")
@patch("tortoise.Tortoise.generate_schemas")
async def test_init_memory_sqlite_decorator_with_models_list(
    mocked_generate: AsyncMock,
    mocked_init: AsyncMock,
    db,
) -> None:
    """Test init_memory_sqlite as decorator with models list."""

    @init_memory_sqlite(["app.models"])
    async def run():
        return "result"

    result = await run()
    assert result == "result"
    mocked_init.assert_awaited_once_with(
        db_url="sqlite://:memory:", modules={"models": ["app.models"]}
    )
    mocked_generate.assert_awaited_once()


@pytest.mark.asyncio
@requireCapability(dialect="sqlite")
@patch("tortoise.Tortoise.init")
@patch("tortoise.Tortoise.generate_schemas")
async def test_init_memory_sqlite_decorator_with_models_string(
    mocked_generate: AsyncMock,
    mocked_init: AsyncMock,
    db,
) -> None:
    """Test init_memory_sqlite as decorator with models string."""

    @init_memory_sqlite("app.models")
    async def run():
        return "result"

    result = await run()
    assert result == "result"
    mocked_init.assert_awaited_once_with(
        db_url="sqlite://:memory:", modules={"models": ["app.models"]}
    )
    mocked_generate.assert_awaited_once()
