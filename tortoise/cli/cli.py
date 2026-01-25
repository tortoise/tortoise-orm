from __future__ import annotations

import contextlib
import importlib
import importlib.util
import platform
import sys
from collections.abc import AsyncGenerator, Iterable
from pathlib import Path
from typing import Any

import asyncclick as click
from ptpython.repl import embed

from tortoise import Tortoise, __version__, connections
from tortoise.cli import utils
from tortoise.migrations.api import migrate as migrate_api
from tortoise.migrations.autodetector import MigrationAutodetector
from tortoise.migrations.executor import PlanStep
from tortoise.migrations.graph import MigrationKey
from tortoise.migrations.loader import MigrationLoader
from tortoise.migrations.recorder import MigrationRecorder
from tortoise.migrations.writer import MigrationWriter, format_migration_name

if platform.system() == "Windows":
    # Remove when prompt-toolkit/ptpython#582 is fixed.
    from asyncio import get_event_loop_policy

    def _patch_loop_factory_for_ptpython() -> None:
        def do_nothing(*_args, **_kwargs) -> None:
            return None

        policy = get_event_loop_policy()
        if loop_factory := getattr(policy, "_loop_factory", None):
            for attr in ("add_signal_handler", "remove_signal_handler"):
                setattr(loop_factory, attr, do_nothing)

    _patch_loop_factory_for_ptpython()


@contextlib.asynccontextmanager
async def aclose_tortoise() -> AsyncGenerator[None]:
    try:
        yield
    finally:
        if Tortoise._inited:
            await connections.close_all()


class _NoopRecorder(MigrationRecorder):
    def __init__(self) -> None:
        super().__init__(connection=None)

    async def applied_migrations(self) -> list[MigrationKey]:
        return []

    async def ensure_schema(self, _schema_editor) -> None:
        return None


def _load_config(ctx: click.Context) -> dict[str, Any]:
    config_value = ctx.obj.get("config")
    config_file = ctx.obj.get("config_file")
    if config_file:
        return Tortoise._get_config_from_config_file(config_file)
    if not config_value:
        config_value = utils.tortoise_orm_config()
    if not config_value:
        raise click.UsageError(
            "You must specify TORTOISE_ORM in option or env, or pyproject.toml [tool.tortoise]",
            ctx=ctx,
        )
    return utils.get_tortoise_config(ctx, config_value)


def _normalized_config(config: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(config)
    apps_config = config.get("apps", {})
    normalized["apps"] = utils.normalize_apps_config(apps_config)
    return normalized


def _select_apps(
    apps_config: dict[str, dict[str, Any]], app_labels: Iterable[str] | None
) -> dict[str, dict[str, Any]]:
    if not apps_config:
        raise click.ClickException("No apps configured in TORTOISE_ORM")
    if not app_labels:
        return apps_config
    selected: dict[str, dict[str, Any]] = {}
    for label in app_labels:
        if label not in apps_config:
            raise click.UsageError(f"Unknown app label {label}")
        selected[label] = apps_config[label]
    return selected


def _group_apps_by_connection(
    apps_config: dict[str, dict[str, Any]],
) -> dict[str, dict[str, dict[str, Any]]]:
    apps_by_connection: dict[str, dict[str, dict[str, Any]]] = {}
    for label, app_config in apps_config.items():
        connection_name = app_config.get("default_connection", "default")
        apps_by_connection.setdefault(connection_name, {})[label] = app_config
    return apps_by_connection


def _ensure_migrations_package(app_label: str, app_config: dict[str, Any]) -> tuple[str, Path]:
    migrations_module = app_config.get("migrations")
    if not migrations_module:
        migrations_module = utils.infer_migrations_module(app_config.get("models"))
    if not migrations_module:
        raise click.ClickException(
            f"Cannot infer migrations module for app {app_label}; set apps.{app_label}.migrations"
        )

    if "." not in migrations_module:
        spec = importlib.util.find_spec(migrations_module)
        if spec and spec.submodule_search_locations:
            package_path = Path(next(iter(spec.submodule_search_locations)))
        elif spec and spec.origin and spec.origin != "built-in":
            raise click.ClickException(
                f"Migrations module {migrations_module} exists but is not a package"
            )
        else:
            package_path = Path.cwd() / migrations_module
            package_path.mkdir(parents=True, exist_ok=True)
            init_path = package_path / "__init__.py"
            if not init_path.exists():
                init_path.write_text("", encoding="utf-8")
            importlib.invalidate_caches()
        return migrations_module, package_path

    parent_module_name, package_name = migrations_module.rsplit(".", 1)
    try:
        parent_module = importlib.import_module(parent_module_name)
    except ModuleNotFoundError as exc:
        raise click.ClickException(
            f"Cannot import parent module {parent_module_name} for app {app_label}: {exc}"
        ) from None

    if hasattr(parent_module, "__path__"):
        parent_path = Path(next(iter(parent_module.__path__)))
    else:
        module_file = getattr(parent_module, "__file__", None)
        if not module_file:
            raise click.ClickException(
                f"Cannot resolve filesystem path for module {parent_module_name}"
            )
        parent_path = Path(module_file).parent

    package_path = parent_path / package_name
    package_path.mkdir(parents=True, exist_ok=True)
    init_path = package_path / "__init__.py"
    if not init_path.exists():
        init_path.write_text("", encoding="utf-8")
    importlib.invalidate_caches()
    return migrations_module, package_path


def _echo_connection_header(connection_name: str, *, suffix: str = "") -> None:
    click.secho(f"Connection: {connection_name}{suffix}", fg="cyan", bold=True)


def _echo_app_header(app_label: str) -> None:
    click.secho(f"  {app_label}:", fg="yellow", bold=True)


def _emit_history(
    applied: list[MigrationKey],
    connection_name: str,
    apps_config: dict[str, dict[str, Any]],
) -> None:
    by_app: dict[str, list[str]] = {label: [] for label in apps_config}
    for key in applied:
        if key.app_label in by_app:
            by_app[key.app_label].append(key.name)
    _echo_connection_header(connection_name)
    for app_label in sorted(by_app):
        _echo_app_header(app_label)
        names = by_app[app_label]
        if not names:
            click.secho("    (no applied migrations)", fg="bright_black")
            continue
        for name in names:
            click.secho(f"    - {app_label} {name}", fg="green")


def _emit_heads(
    loader: MigrationLoader,
    connection_name: str,
    apps_config: dict[str, dict[str, Any]],
) -> None:
    _echo_connection_header(connection_name)
    for app_label in sorted(apps_config):
        _echo_app_header(app_label)
        keys = list(loader.graph.leaf_nodes(app_label))
        if not keys:
            click.secho("    (no heads)", fg="bright_black")
            continue
        for key in keys:
            click.secho(f"    - {app_label}.{key.name}", fg="blue")


def _emit_migration_plan(
    connection_name: str,
    plan: list[PlanStep],
    fake: bool,
    dry_run: bool,
) -> None:
    suffixes = []
    if dry_run:
        suffixes.append("dry-run")
    if fake:
        suffixes.append("fake")
    suffix = f" ({', '.join(suffixes)})" if suffixes else ""
    _echo_connection_header(connection_name, suffix=suffix)
    if not plan:
        click.secho("  No migrations to apply", fg="bright_black")
        return
    applied = 0
    rolled_back = 0
    for step in plan:
        label = f"{step.migration.app_label}.{step.migration.name}"
        if step.backward:
            rolled_back += 1
            click.secho(f"  ROLLBACK  {label}", fg="red")
        else:
            applied += 1
            click.secho(f"  APPLY     {label}", fg="green")
    click.secho(
        f"  Plan: {applied} apply, {rolled_back} rollback",
        fg="cyan",
    )


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, "-V", "--version")
@click.option(
    "-c",
    "--config",
    help="TortoiseORM config dictionary path, like settings.TORTOISE_ORM",
)
@click.option(
    "--config-file",
    help="Path to a JSON/YAML config file for TortoiseORM",
)
@click.pass_context
async def cli(ctx: click.Context, config: str | None, config_file: str | None) -> None:
    ctx.ensure_object(dict)
    ctx.obj["config"] = config
    ctx.obj["config_file"] = config_file


@cli.command(help="Create migrations packages for configured apps.")
@click.argument("app_labels", nargs=-1)
@click.pass_context
async def init(ctx: click.Context, app_labels: tuple[str, ...]) -> None:
    config = _normalized_config(_load_config(ctx))
    apps_config = _select_apps(config.get("apps", {}), app_labels or None)
    for label, app_config in apps_config.items():
        module, path = _ensure_migrations_package(label, app_config)
        click.echo(f"{label}: {module} -> {path}")


@cli.command(help="Start an interactive shell.")
@click.pass_context
async def shell(ctx: click.Context) -> None:
    config = _normalized_config(_load_config(ctx))
    async with aclose_tortoise():
        await Tortoise.init(config=config, init_connections=False)
        with contextlib.suppress(EOFError, ValueError):
            await embed(
                globals=globals(),
                title="Tortoise Shell",
                vi_mode=True,
                return_asyncio_coroutine=True,
                patch_stdout=True,
            )


@cli.command(help="Create new migrations from model changes.")
@click.argument("app_labels", nargs=-1)
@click.option("--empty", is_flag=True, help="Create an empty migration.")
@click.option("-n", "--name", help="Use this name for the migration file.")
@click.pass_context
async def makemigrations(
    ctx: click.Context, app_labels: tuple[str, ...], empty: bool, name: str | None
) -> None:
    if empty and not app_labels:
        raise click.UsageError("--empty requires at least one APP_LABEL", ctx=ctx)
    config = _normalized_config(_load_config(ctx))
    apps_config = _select_apps(config.get("apps", {}), app_labels or None)
    for label, app_config in apps_config.items():
        migrations_module, _ = _ensure_migrations_package(label, app_config)
        app_config["migrations"] = migrations_module
    config["apps"] = apps_config

    async with aclose_tortoise():
        await Tortoise.init(config=config)
        if not Tortoise.apps:
            raise click.ClickException("Tortoise apps are not initialized")
        autodetector = MigrationAutodetector(Tortoise.apps, apps_config)
        if empty:
            await autodetector.loader.build_graph()
            old_state = await autodetector._project_state()
            new_state = autodetector._current_state()
            writers = []
            for label, app_config in apps_config.items():
                migrations_module_name = app_config.get("migrations")
                if not isinstance(migrations_module_name, str):
                    continue
                dependencies = sorted(
                    [(key.app_label, key.name) for key in autodetector._leaf_nodes(label)]
                )
                migration_name, initial = autodetector._migration_name(label, old_state, new_state)
                writers.append(
                    MigrationWriter(
                        migration_name,
                        label,
                        [],
                        dependencies=dependencies,
                        initial=initial,
                        migrations_module=migrations_module_name,
                    )
                )
        else:
            writers = await autodetector.changes()

    if not writers:
        click.secho("No changes detected", fg="yellow")
        return

    for writer in writers:
        if name:
            try:
                number = int(writer.name.split("_", 1)[0])
            except ValueError:
                number = 1
            writer.name = format_migration_name(number, name)
        path = writer.write()
        click.secho(
            f"Created {writer.app_label}.{writer.name}",
            fg="green",
            bold=True,
        )
        click.secho(f"  {path}", fg="blue")


async def _run_migrate(
    ctx: click.Context,
    app_label: str | None,
    migration: str | None,
    *,
    fake: bool,
    dry_run: bool,
    target_override: str | None = None,
    direction: str = "both",
) -> None:
    if app_label and not migration and "." in app_label:
        app_label, migration = app_label.split(".", 1)

    config = _normalized_config(_load_config(ctx))

    target = target_override
    if target is None:
        if app_label and not migration:
            target = f"{app_label}.__latest__"
        elif migration:
            if not app_label:
                raise click.UsageError("MIGRATION requires APP_LABEL")
            target = f"{app_label}.{migration}"

    async with aclose_tortoise():
        await migrate_api(
            config=config,
            app_labels=None,
            target=target,
            fake=fake,
            dry_run=dry_run,
            direction=direction,
            reporter=_emit_migration_plan,
        )


@cli.command(help="Apply migrations.")
@click.argument("app_label", required=False)
@click.argument("migration", required=False)
@click.option("--fake", is_flag=True, help="Record migrations without executing SQL.")
@click.option("--dry-run", is_flag=True, help="Show what would run without changing DB state.")
@click.pass_context
async def migrate(
    ctx: click.Context,
    app_label: str | None,
    migration: str | None,
    fake: bool,
    dry_run: bool,
) -> None:
    await _run_migrate(ctx, app_label, migration, fake=fake, dry_run=dry_run)


@cli.command(help="Apply migrations (alias for migrate).")
@click.argument("app_label", required=False)
@click.argument("migration", required=False)
@click.option("--fake", is_flag=True, help="Record migrations without executing SQL.")
@click.option("--dry-run", is_flag=True, help="Show what would run without changing DB state.")
@click.pass_context
async def upgrade(
    ctx: click.Context,
    app_label: str | None,
    migration: str | None,
    fake: bool,
    dry_run: bool,
) -> None:
    await _run_migrate(
        ctx,
        app_label,
        migration,
        fake=fake,
        dry_run=dry_run,
        direction="forward",
    )


@cli.command(help="Unapply migrations.")
@click.argument("app_label", required=True)
@click.argument("migration", required=False)
@click.option("--fake", is_flag=True, help="Record migrations without executing SQL.")
@click.option("--dry-run", is_flag=True, help="Show what would run without changing DB state.")
@click.pass_context
async def downgrade(
    ctx: click.Context,
    app_label: str,
    migration: str | None,
    fake: bool,
    dry_run: bool,
) -> None:
    if not migration and "." in app_label:
        app_label, migration = app_label.split(".", 1)
    if migration:
        target = f"{app_label}.{migration}"
    else:
        target = f"{app_label}.__first__"
    await _run_migrate(
        ctx,
        app_label,
        migration,
        fake=fake,
        dry_run=dry_run,
        target_override=target,
        direction="backward",
    )


@cli.command(help="List applied migrations from the database.")
@click.argument("app_labels", nargs=-1)
@click.pass_context
async def history(ctx: click.Context, app_labels: tuple[str, ...]) -> None:
    config = _normalized_config(_load_config(ctx))
    apps_config = _select_apps(config.get("apps", {}), app_labels or None)
    config["apps"] = apps_config
    apps_by_connection = _group_apps_by_connection(apps_config)

    async with aclose_tortoise():
        await Tortoise.init(config=config)
        for connection_name, subset in apps_by_connection.items():
            recorder = MigrationRecorder(connections.get(connection_name))
            applied = await recorder.applied_migrations()
            _emit_history(applied, connection_name, subset)


@cli.command(help="List migration heads on disk.")
@click.argument("app_labels", nargs=-1)
@click.pass_context
async def heads(ctx: click.Context, app_labels: tuple[str, ...]) -> None:
    config = _normalized_config(_load_config(ctx))
    apps_config = _select_apps(config.get("apps", {}), app_labels or None)
    config["apps"] = apps_config
    apps_by_connection = _group_apps_by_connection(apps_config)

    loader = MigrationLoader(apps_config, _NoopRecorder(), load=False)
    await loader.build_graph()

    for connection_name, subset in apps_by_connection.items():
        _emit_heads(loader, connection_name, subset)


def main() -> None:
    if sys.path[0] != ".":
        sys.path.insert(0, ".")
    cli()


if __name__ == "__main__":
    main()
