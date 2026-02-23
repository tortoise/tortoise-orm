from __future__ import annotations

from typing import Any

from tortoise import Tortoise
from tortoise.config import TortoiseConfig
from tortoise.connection import get_connection
from tortoise.migrations.executor import MigrationExecutor
from tortoise.migrations.graph import MigrationKey
from tortoise.migrations.recorder import MigrationRecorder


class _NoopRecorder(MigrationRecorder):
    """A recorder that returns no applied migrations and never touches the DB."""

    def __init__(self) -> None:
        super().__init__(connection=None)

    async def applied_migrations(self) -> list[MigrationKey]:
        return []

    async def ensure_schema(self, _schema_editor: Any) -> None:
        return None


async def sqlmigrate(
    *,
    config: dict[str, Any] | TortoiseConfig | None = None,
    config_file: str | None = None,
    app_label: str,
    migration_name: str,
    backward: bool = False,
) -> list[str]:
    """Collect the SQL statements for a single migration without executing them.

    Args:
        config: Tortoise ORM config dict or TortoiseConfig object.
        config_file: Path to a JSON/YAML config file for Tortoise ORM.
        app_label: The application label.
        migration_name: The migration name (exact or prefix match).
        backward: If True, collect SQL for unapplying the migration.

    Returns:
        A list of SQL strings (including descriptive comment annotations).
    """
    if isinstance(config, TortoiseConfig):
        config = config.to_dict()
    if config_file:
        config = Tortoise._get_config_from_config_file(config_file)
    if not config:
        raise ValueError("sqlmigrate requires a config or config_file")

    await Tortoise.init(config=config, init_connections=False)

    configured_apps = config.get("apps", {})
    if app_label not in configured_apps:
        raise ValueError(f"Unknown app label {app_label!r}")

    app_config = configured_apps[app_label]
    connection_name = app_config.get("default_connection", "default")
    connection = get_connection(connection_name)

    apps_config = {app_label: app_config}
    executor = MigrationExecutor(connection, apps_config)
    # Replace the recorder with a noop so build_graph() does not query the DB.
    executor.loader.recorder = _NoopRecorder()

    return await executor.collect_sql(app_label, migration_name, backward=backward)
