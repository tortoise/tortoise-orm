from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from tortoise import Tortoise
from tortoise.config import TortoiseConfig
from tortoise.connection import get_connection
from tortoise.migrations.executor import MigrationExecutor, MigrationTarget, PlanStep


async def plan(
    *,
    config: dict[str, Any] | TortoiseConfig | None = None,
    config_file: str | None = None,
    app_labels: Sequence[str] | None = None,
    target: str | None = None,
) -> list[str]:
    """
    Print an ordered migration plan and return the formatted lines.
    """
    if isinstance(config, TortoiseConfig):
        config = config.to_dict()
    if config_file:
        config = Tortoise._get_config_from_config_file(config_file)
    if not config:
        raise ValueError("plan requires a config or config_file")

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
    output: list[str] = []
    for connection_name, subset in apps_by_connection.items():
        connection = get_connection(connection_name)
        executor = MigrationExecutor(connection, subset)
        executor_targets = [t for t in targets if t.app_label in subset]
        steps = await executor.plan(executor_targets if executor_targets else None)
        output.extend(_format_steps(steps, connection_name))

    for line in output:
        print(line)
    return output


def _format_steps(steps: list[PlanStep], connection_name: str) -> list[str]:
    lines = [f"# Connection: {connection_name}"]
    for step in steps:
        prefix = "-" if step.backward else "+"
        lines.append(f"{prefix} {step.migration.app_label}.{step.migration.name}")
    return lines


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
