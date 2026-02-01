from __future__ import annotations

import argparse
import asyncio
import contextlib
import importlib
import importlib.util
import platform
import sys
from collections.abc import AsyncGenerator, Iterable
from pathlib import Path
from typing import Any

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


def _load_config(ctx: CLIContext) -> dict[str, Any]:
    config_value = ctx.config
    config_file = ctx.config_file
    if config_file:
        return Tortoise._get_config_from_config_file(config_file)
    if not config_value:
        config_value = utils.tortoise_orm_config()
    if not config_value:
        raise utils.CLIUsageError(
            "You must specify TORTOISE_ORM in option or env, or pyproject.toml [tool.tortoise]",
        )
    return utils.get_tortoise_config(config_value)


def _normalized_config(config: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(config)
    apps_config = config.get("apps", {})
    normalized["apps"] = utils.normalize_apps_config(apps_config)
    return normalized


def _select_apps(
    apps_config: dict[str, dict[str, Any]], app_labels: Iterable[str] | None
) -> dict[str, dict[str, Any]]:
    if not apps_config:
        raise utils.CLIError("No apps configured in TORTOISE_ORM")
    if not app_labels:
        return apps_config
    selected: dict[str, dict[str, Any]] = {}
    for label in app_labels:
        if label not in apps_config:
            raise utils.CLIUsageError(f"Unknown app label {label}")
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
        raise utils.CLIError(
            f"Cannot infer migrations module for app {app_label}; set apps.{app_label}.migrations"
        )

    if "." not in migrations_module:
        spec = importlib.util.find_spec(migrations_module)
        if spec and spec.submodule_search_locations:
            package_path = Path(next(iter(spec.submodule_search_locations)))
        elif spec and spec.origin and spec.origin != "built-in":
            raise utils.CLIError(
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
        raise utils.CLIError(
            f"Cannot import parent module {parent_module_name} for app {app_label}: {exc}"
        ) from None

    if hasattr(parent_module, "__path__"):
        parent_path = Path(next(iter(parent_module.__path__)))
    else:
        module_file = getattr(parent_module, "__file__", None)
        if not module_file:
            raise utils.CLIError(f"Cannot resolve filesystem path for module {parent_module_name}")
        parent_path = Path(module_file).parent

    package_path = parent_path / package_name
    package_path.mkdir(parents=True, exist_ok=True)
    init_path = package_path / "__init__.py"
    if not init_path.exists():
        init_path.write_text("", encoding="utf-8")
    importlib.invalidate_caches()
    return migrations_module, package_path


def _echo_connection_header(connection_name: str, *, suffix: str = "") -> None:
    print(f"Connection: {connection_name}{suffix}")


def _echo_app_header(app_label: str) -> None:
    print(f"  {app_label}:")


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
            print("    (no applied migrations)")
            continue
        for name in names:
            print(f"    - {app_label} {name}")


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
            print("    (no heads)")
            continue
        for key in keys:
            print(f"    - {app_label}.{key.name}")


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
        print("  No migrations to apply")
        return
    applied = 0
    rolled_back = 0
    for step in plan:
        label = f"{step.migration.app_label}.{step.migration.name}"
        if step.backward:
            rolled_back += 1
            print(f"  ROLLBACK  {label}")
        else:
            applied += 1
            print(f"  APPLY     {label}")
    print(f"  Plan: {applied} apply, {rolled_back} rollback")


class CLIContext:
    def __init__(self, config: str | None, config_file: str | None) -> None:
        self.config = config
        self.config_file = config_file


async def init(ctx: CLIContext, app_labels: tuple[str, ...]) -> None:
    config = _normalized_config(_load_config(ctx))
    apps_config = _select_apps(config.get("apps", {}), app_labels or None)
    for label, app_config in apps_config.items():
        module, path = _ensure_migrations_package(label, app_config)
        print(f"{label}: {module} -> {path}")


async def shell(ctx: CLIContext) -> None:
    config = _normalized_config(_load_config(ctx))
    async with aclose_tortoise():
        await Tortoise.init(config=config)
        with contextlib.suppress(EOFError, ValueError):
            await embed(
                globals=globals(),
                title="Tortoise Shell",
                vi_mode=True,
                return_asyncio_coroutine=True,
                patch_stdout=True,
            )


async def makemigrations(
    ctx: CLIContext, app_labels: tuple[str, ...], empty: bool, name: str | None
) -> None:
    if empty and not app_labels:
        raise utils.CLIUsageError("--empty requires at least one APP_LABEL")
    config = _normalized_config(_load_config(ctx))
    apps_config = _select_apps(config.get("apps", {}), app_labels or None)
    for label, app_config in apps_config.items():
        migrations_module, _ = _ensure_migrations_package(label, app_config)
        app_config["migrations"] = migrations_module
    config["apps"] = apps_config

    async with aclose_tortoise():
        await Tortoise.init(config=config)
        if not Tortoise.apps:
            raise utils.CLIError("Tortoise apps are not initialized")
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
        print("No changes detected")
        return

    for writer in writers:
        if name:
            try:
                number = int(writer.name.split("_", 1)[0])
            except ValueError:
                number = 1
            writer.name = format_migration_name(number, name)
        path = writer.write()
        print(f"Created {writer.app_label}.{writer.name}")
        print(f"  {path}")


async def _run_migrate(
    ctx: CLIContext,
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
                raise utils.CLIUsageError("MIGRATION requires APP_LABEL")
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


async def migrate(
    ctx: CLIContext,
    app_label: str | None,
    migration: str | None,
    fake: bool,
    dry_run: bool,
) -> None:
    await _run_migrate(ctx, app_label, migration, fake=fake, dry_run=dry_run)


async def upgrade(
    ctx: CLIContext,
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


async def downgrade(
    ctx: CLIContext,
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


async def history(ctx: CLIContext, app_labels: tuple[str, ...]) -> None:
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


async def heads(ctx: CLIContext, app_labels: tuple[str, ...]) -> None:
    config = _normalized_config(_load_config(ctx))
    apps_config = _select_apps(config.get("apps", {}), app_labels or None)
    config["apps"] = apps_config
    apps_by_connection = _group_apps_by_connection(apps_config)

    loader = MigrationLoader(apps_config, _NoopRecorder(), load=False)
    await loader.build_graph()

    for connection_name, subset in apps_by_connection.items():
        _emit_heads(loader, connection_name, subset)


def _add_global_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-c",
        "--config",
        help="TortoiseORM config dictionary path, like settings.TORTOISE_ORM",
    )
    parser.add_argument(
        "--config-file",
        help="Path to a JSON/YAML config file for TortoiseORM",
    )
    parser.add_argument("-V", "--version", action="version", version=__version__)


def _add_init_parser(subparsers: argparse._SubParsersAction) -> None:
    init_parser = subparsers.add_parser(
        "init", help="Create migrations packages for configured apps."
    )
    init_parser.add_argument("app_labels", nargs="*")
    init_parser.set_defaults(func=_run_init)


def _add_shell_parser(subparsers: argparse._SubParsersAction) -> None:
    shell_parser = subparsers.add_parser("shell", help="Start an interactive shell.")
    shell_parser.set_defaults(func=_run_shell)


def _add_makemigrations_parser(subparsers: argparse._SubParsersAction) -> None:
    makemigrations_parser = subparsers.add_parser(
        "makemigrations", help="Create new migrations from model changes."
    )
    makemigrations_parser.add_argument("app_labels", nargs="*")
    makemigrations_parser.add_argument(
        "--empty", action="store_true", help="Create an empty migration."
    )
    makemigrations_parser.add_argument("-n", "--name", help="Use this name for the migration file.")
    makemigrations_parser.set_defaults(func=_run_makemigrations)


def _add_migrate_parser(subparsers: argparse._SubParsersAction) -> None:
    migrate_parser = subparsers.add_parser("migrate", help="Apply migrations.")
    migrate_parser.add_argument("app_label", nargs="?")
    migrate_parser.add_argument("migration", nargs="?")
    migrate_parser.add_argument(
        "--fake", action="store_true", help="Record migrations without executing SQL."
    )
    migrate_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would run without changing DB state."
    )
    migrate_parser.set_defaults(func=_run_migrate_cmd)


def _add_upgrade_parser(subparsers: argparse._SubParsersAction) -> None:
    upgrade_parser = subparsers.add_parser("upgrade", help="Apply migrations (alias for migrate).")
    upgrade_parser.add_argument("app_label", nargs="?")
    upgrade_parser.add_argument("migration", nargs="?")
    upgrade_parser.add_argument(
        "--fake", action="store_true", help="Record migrations without executing SQL."
    )
    upgrade_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would run without changing DB state."
    )
    upgrade_parser.set_defaults(func=_run_upgrade)


def _add_downgrade_parser(subparsers: argparse._SubParsersAction) -> None:
    downgrade_parser = subparsers.add_parser("downgrade", help="Unapply migrations.")
    downgrade_parser.add_argument("app_label")
    downgrade_parser.add_argument("migration", nargs="?")
    downgrade_parser.add_argument(
        "--fake", action="store_true", help="Record migrations without executing SQL."
    )
    downgrade_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would run without changing DB state."
    )
    downgrade_parser.set_defaults(func=_run_downgrade)


def _add_history_parser(subparsers: argparse._SubParsersAction) -> None:
    history_parser = subparsers.add_parser(
        "history", help="List applied migrations from the database."
    )
    history_parser.add_argument("app_labels", nargs="*")
    history_parser.set_defaults(func=_run_history)


def _add_heads_parser(subparsers: argparse._SubParsersAction) -> None:
    heads_parser = subparsers.add_parser("heads", help="List migration heads on disk.")
    heads_parser.add_argument("app_labels", nargs="*")
    heads_parser.set_defaults(func=_run_heads)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tortoise")
    _add_global_options(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)

    _add_init_parser(subparsers)
    _add_shell_parser(subparsers)
    _add_makemigrations_parser(subparsers)
    _add_migrate_parser(subparsers)
    _add_upgrade_parser(subparsers)
    _add_downgrade_parser(subparsers)
    _add_history_parser(subparsers)
    _add_heads_parser(subparsers)

    return parser


async def _run_init(ctx: CLIContext, args: argparse.Namespace) -> None:
    await init(ctx, tuple(args.app_labels))


async def _run_shell(ctx: CLIContext, _args: argparse.Namespace) -> None:
    await shell(ctx)


async def _run_makemigrations(ctx: CLIContext, args: argparse.Namespace) -> None:
    await makemigrations(ctx, tuple(args.app_labels), args.empty, args.name)


async def _run_migrate_cmd(ctx: CLIContext, args: argparse.Namespace) -> None:
    await migrate(ctx, args.app_label, args.migration, args.fake, args.dry_run)


async def _run_upgrade(ctx: CLIContext, args: argparse.Namespace) -> None:
    await upgrade(ctx, args.app_label, args.migration, args.fake, args.dry_run)


async def _run_downgrade(ctx: CLIContext, args: argparse.Namespace) -> None:
    await downgrade(ctx, args.app_label, args.migration, args.fake, args.dry_run)


async def _run_history(ctx: CLIContext, args: argparse.Namespace) -> None:
    await history(ctx, tuple(args.app_labels))


async def _run_heads(ctx: CLIContext, args: argparse.Namespace) -> None:
    await heads(ctx, tuple(args.app_labels))


async def run_cli_async(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1

    ctx = CLIContext(config=args.config, config_file=args.config_file)
    try:
        await args.func(ctx, args)
    except utils.CLIUsageError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except utils.CLIError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


def main() -> None:
    if sys.path[0] != ".":
        sys.path.insert(0, ".")
    raise SystemExit(asyncio.run(run_cli_async()))


if __name__ == "__main__":
    main()
