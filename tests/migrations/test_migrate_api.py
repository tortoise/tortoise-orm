import pytest

from tortoise import Tortoise
from tortoise.config import AppConfig, ConnectionConfig, TortoiseConfig
from tortoise.migrations.api import migrate


@pytest.mark.asyncio
async def test_migrate_accepts_dataclass_config() -> None:
    config = TortoiseConfig(
        connections={
            "default": ConnectionConfig(
                engine="tortoise.backends.sqlite",
                credentials={"file_path": ":memory:"},
            )
        },
        apps={"models": AppConfig(models=["tests.testmodels"], default_connection="default")},
    )
    try:
        await migrate(config=config)
    finally:
        await Tortoise.close_connections()
