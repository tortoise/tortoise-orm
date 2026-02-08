from __future__ import annotations

import inspect
from collections.abc import Callable, Sequence
from typing import Any

from tortoise import Tortoise
from tortoise.config import TortoiseConfig
from tortoise.connection import get_connection
from tortoise.migrations.executor import MigrationExecutor, MigrationTarget, PlanStep


async def migrate(
    *,
    config: dict[str, Any] | TortoiseConfig | None = None,
    config_file: str | None = None,
    app_labels: Sequence[str] | None = None,
    target: str | None = None,
    fake: bool = False,
    dry_run: bool = False,
    direction: str = "both",
    reporter: Callable[[str, list[PlanStep], bool, bool], object] | None = None,
    progress: Callable[[str, str, str], object] | None = None,
) -> None:
    """Run migrations for configured apps."""
    if isinstance(config, TortoiseConfig):
        config = config.to_dict()
    if config_file:
        config = Tortoise._get_config_from_config_file(config_file)
    if not config:
        raise ValueError("migrate requires a config or config_file")

    await Tortoise.init(config=config, init_connections=False)

    configured_apps = config.get("apps", {})
    selected_apps = list(app_labels) if app_labels else list(configured_apps.keys())
    for label in selected_apps:
        if label not in configured_apps:
            raise ValueError(f"Unknown app label {label}")

    apps_config = {label: configured_apps[label] for label in selected_apps}
    apps_by_connection: dict[str, dict[str, dict[str, Any]]] = {}
    for label, app_config in apps_config.items():
        connection_name = app_config.get("default_connection", "default")
        apps_by_connection.setdefault(connection_name, {})[label] = app_config

    targets = _parse_targets(target, selected_apps)
    for connection_name, subset in apps_by_connection.items():
        connection = get_connection(connection_name)
        executor = MigrationExecutor(connection, subset)
        executor_targets = [t for t in targets if t.app_label in subset]
        if reporter is not None:
            plan = await executor.plan(executor_targets if executor_targets else None)
            result = reporter(connection_name, plan, fake, dry_run)
            if inspect.isawaitable(result):
                await result
        await executor.migrate(
            executor_targets if executor_targets else None,
            fake=fake,
            dry_run=dry_run,
            direction=direction,
            progress=progress,
        )


def _parse_targets(target: str | None, app_labels: Sequence[str]) -> list[MigrationTarget]:
    if not target:
        return [MigrationTarget(app_label=label, name="__latest__") for label in app_labels]
    if "." in target:
        app_label, name = target.split(".", 1)
        if app_label not in app_labels:
            raise ValueError(f"Unknown app label {app_label}")
        return [MigrationTarget(app_label=app_label, name=name)]
    if target not in app_labels:
        raise ValueError(f"Unknown app label {target}")
    return [MigrationTarget(app_label=target, name="__latest__")]
