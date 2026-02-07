from __future__ import annotations

import argparse
import asyncio
import contextlib
import importlib
import importlib.util
import os
import platform
import sys
from collections.abc import AsyncGenerator, Iterable
from enum import Enum
from pathlib import Path
from typing import Any

try:
    from IPython.terminal.embed import embed as ipython_embed

    HAS_IPYTHON = True
except ImportError:
    ipython_embed = None
    HAS_IPYTHON = False

try:
    from ptpython.repl import embed as ptpython_embed

    HAS_PTPYTHON = True
except ImportError:
    ptpython_embed = None
    HAS_PTPYTHON = False

from tortoise import Tortoise, __version__
from tortoise.cli import utils
from tortoise.config import AppConfig, TortoiseConfig
from tortoise.connection import get_connection
from tortoise.context import TortoiseContext
from tortoise.migrations.api import migrate as migrate_api
from tortoise.migrations.api import sqlmigrate as sqlmigrate_api
from tortoise.migrations.autodetector import MigrationAutodetector
from tortoise.migrations.executor import PlanStep
from tortoise.migrations.graph import MigrationKey
from tortoise.migrations.loader import MigrationLoader
from tortoise.migrations.recorder import MigrationRecorder
from tortoise.migrations.writer import MigrationWriter, format_migration_name

if platform.system() == "Windows":
    # Windows-specific patch for ptpython signal handler issues
    # Only applied when launching ptpython shell on Windows
    # Remove when prompt-toolkit/ptpython#582 is fixed.
    from asyncio import get_event_loop_policy

    def _patch_loop_factory_for_ptpython() -> None:
        """Patch event loop policy to work around ptpython signal handler bug on Windows."""

        def do_nothing(*_args, **_kwargs) -> None:
            return None

        policy = get_event_loop_policy()
        if loop_factory := getattr(policy, "_loop_factory", None):
            for attr in ("add_signal_handler", "remove_signal_handler"):
                setattr(loop_factory, attr, do_nothing)


class ShellProvider(Enum):
    IPYTHON = "ipython"
    PTPYTHON = "ptpython"


def _get_available_shell_provider() -> ShellProvider | None:
    if HAS_IPYTHON:
        return ShellProvider.IPYTHON
    elif HAS_PTPYTHON:
        return ShellProvider.PTPYTHON
    return None


def _launch_ipython_shell(namespace: dict[str, Any]) -> None:
    """Launch IPython shell synchronously.

    IPython manages its own event loop for autoawait, so this must be called
    from a synchronous context to avoid nested event loop errors.

    Args:
        namespace: The namespace dict to make available in the shell
    """
    # Apply nest_asyncio to allow IPython to run its own event loop
    # This is needed because we're already inside an async context
    import nest_asyncio

    nest_asyncio.apply()

    with contextlib.suppress(EOFError, ValueError):
        # Configure IPython for async/await support
        from IPython.terminal.embed import InteractiveShellEmbed

        model_names = [
            k for k in namespace.keys() if k not in ("Tortoise", "tortoise", "connections", "apps")
        ]
        models_info = (
            f"Available models: {', '.join(model_names)}" if model_names else "No models loaded"
        )

        banner = (
            "Tortoise ORM Shell (IPython with async support)\n"
            f"{models_info}\n"
            "Use 'await' directly for async operations (e.g., 'await YourModel.all()').\n"
        )

        # Create IPython shell with async autoawait enabled
        ipshell = InteractiveShellEmbed(
            user_ns=namespace,
            banner1=banner,
        )
        # Enable autoawait for top-level await
        ipshell.autoawait = True
        ipshell()


async def _launch_ptpython_shell(namespace: dict[str, Any]) -> None:
    """Launch ptpython shell asynchronously.

    Args:
        namespace: The namespace dict to make available in the shell
    """
    # Apply Windows patch for ptpython signal handler issues
    if platform.system() == "Windows":
        _patch_loop_factory_for_ptpython()

    model_names = [
        k for k in namespace.keys() if k not in ("Tortoise", "tortoise", "connections", "apps")
    ]

    # Print banner before launching ptpython
    models_info = (
        f"Available models: {', '.join(model_names)}" if model_names else "No models loaded"
    )
    print("Tortoise ORM Shell (ptpython)")
    print(models_info)
    print("Use 'await' directly for async operations (e.g., 'await YourModel.all()').\n")

    with contextlib.suppress(EOFError, ValueError):
        await ptpython_embed(
            globals=namespace,
            title="Tortoise Shell",
            vi_mode=True,
            return_asyncio_coroutine=True,
            patch_stdout=True,
        )


@contextlib.asynccontextmanager
async def tortoise_cli_context(
    config: dict[str, Any] | TortoiseConfig,
) -> AsyncGenerator[TortoiseContext, None]:
    async with TortoiseContext() as ctx:
        await ctx.init(config=config)
        yield ctx


class _NoopRecorder(MigrationRecorder):
    def __init__(self) -> None:
        super().__init__(connection=None)

    async def applied_migrations(self) -> list[MigrationKey]:
        return []

    async def ensure_schema(self, _schema_editor) -> None:
        return None


def _load_config(ctx: CLIContext) -> TortoiseConfig:
    """Load Tortoise ORM configuration from various sources.

    Returns:
        TortoiseConfig: Validated configuration object
    """
    config_value = ctx.config
    config_file = ctx.config_file
    if config_file:
        config_dict = Tortoise._get_config_from_config_file(config_file)
        return TortoiseConfig.from_dict(config_dict)
    if not config_value:
        config_value = utils.tortoise_orm_config()
    if not config_value:
        raise utils.CLIUsageError(
            "You must specify TORTOISE_ORM in option or env, or pyproject.toml [tool.tortoise]",
        )
    return utils.get_tortoise_config(config_value)


def _select_apps(config: TortoiseConfig, app_labels: Iterable[str] | None) -> dict[str, AppConfig]:
    """Select specific apps from config, or all if no labels specified."""
    if not config.apps:
        raise utils.CLIError("No apps configured in TORTOISE_ORM")
    if not app_labels:
        return dict(config.apps)
    selected: dict[str, AppConfig] = {}
    for label in app_labels:
        if label not in config.apps:
            raise utils.CLIUsageError(f"Unknown app label {label}")
        selected[label] = config.apps[label]
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


def _supports_color() -> bool:
    """Check if the terminal supports ANSI colors."""
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return False
    if sys.platform == "win32":
        # Windows 10+ supports ANSI via Virtual Terminal Processing
        return "WT_SESSION" in os.environ or "ANSICON" in os.environ
    return True


_COLOR = _supports_color()

# ANSI color codes
_BOLD = "\033[1m" if _COLOR else ""
_DIM = "\033[2m" if _COLOR else ""
_GREEN = "\033[32m" if _COLOR else ""
_YELLOW = "\033[33m" if _COLOR else ""
_CYAN = "\033[36m" if _COLOR else ""
_RED = "\033[31m" if _COLOR else ""
_RESET = "\033[0m" if _COLOR else ""


def _echo_connection_header(connection_name: str, *, suffix: str = "") -> None:
    print(f"{_BOLD}Connection: {connection_name}{suffix}{_RESET}")


def _echo_app_header(app_label: str) -> None:
    print(f"  {_BOLD}{app_label}:{_RESET}")


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
            print(f"    {_DIM}(no applied migrations){_RESET}")
            continue
        for name in names:
            print(f"    {_GREEN}-{_RESET} {app_label} {name}")


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
            print(f"    {_DIM}(no heads){_RESET}")
            continue
        for key in keys:
            print(f"    {_CYAN}-{_RESET} {app_label}.{key.name}")


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
        print(f"  {_DIM}No migrations to apply{_RESET}")
        return
    applied = 0
    rolled_back = 0
    for step in plan:
        label = f"{step.migration.app_label}.{step.migration.name}"
        if step.backward:
            rolled_back += 1
            print(f"  {_YELLOW}ROLLBACK{_RESET}  {label}")
        else:
            applied += 1
            print(f"  {_CYAN}APPLY{_RESET}     {label}")
    print(f"  {_DIM}Plan: {applied} to apply, {rolled_back} to roll back{_RESET}")


class CLIContext:
    def __init__(self, config: str | None, config_file: str | None) -> None:
        self.config = config
        self.config_file = config_file


async def init(ctx: CLIContext, app_labels: tuple[str, ...]) -> None:
    config = _load_config(ctx)
    apps_config = _select_apps(config, app_labels or None)
    for label, app_config in apps_config.items():
        # Convert AppConfig to dict for _ensure_migrations_package
        app_dict = app_config.to_dict()
        module, path = _ensure_migrations_package(label, app_dict)
        print(f"{label}: {module} -> {path}")


async def shell(ctx: CLIContext) -> None:
    """Launch an interactive shell with Tortoise ORM context.

    Prefers IPython if available, falls back to ptpython.
    Requires at least one shell provider to be installed.

    Raises:
        CLIError: If neither IPython nor ptpython is installed
    """
    # Detect which shell provider is available
    provider = _get_available_shell_provider()

    if provider is None:
        raise utils.CLIError(
            "No interactive shell available. Please install one of the following:\n"
            "  - IPython (recommended): pip install tortoise-orm[ipython]\\n"
            "  - ptpython: pip install tortoise-orm[ptpython]\\n"
            "  - Or install directly: pip install ipython (or ptpython)"
        )

    config = _load_config(ctx)

    # For IPython: Initialize context, prepare namespace, then launch synchronously
    # IPython manages its own event loop for autoawait
    if provider == ShellProvider.IPYTHON:
        async with tortoise_cli_context(config) as tortoise_ctx:
            # Prepare namespace with Tortoise context and useful imports
            namespace = {
                "Tortoise": Tortoise,
                "tortoise": tortoise_ctx,
                "apps": tortoise_ctx.apps,
            }
            # Add all models to namespace for easy access
            if tortoise_ctx.apps:
                for app_name, models_dict in tortoise_ctx.apps.items():
                    for model_name, model_class in models_dict.items():
                        namespace[model_name] = model_class

            # Launch IPython synchronously - it will manage its own event loop
            _launch_ipython_shell(namespace)
    else:
        # ptpython works fine in async context
        async with tortoise_cli_context(config) as tortoise_ctx:
            # Prepare namespace with Tortoise context and useful imports
            namespace = {
                "Tortoise": Tortoise,
                "tortoise": tortoise_ctx,
                "apps": tortoise_ctx.apps,
            }
            # Add all models to namespace for easy access
            if tortoise_ctx.apps:
                for app_name, models_dict in tortoise_ctx.apps.items():
                    for model_name, model_class in models_dict.items():
                        namespace[model_name] = model_class

            await _launch_ptpython_shell(namespace)


async def makemigrations(
    ctx: CLIContext, app_labels: tuple[str, ...], empty: bool, name: str | None
) -> None:
    if empty and not app_labels:
        raise utils.CLIUsageError("--empty requires at least one APP_LABEL")
    tortoise_config = _load_config(ctx)
    apps_config = _select_apps(tortoise_config, app_labels or None)

    apps_dict = {label: app.to_dict() for label, app in apps_config.items()}
    for label, app_config in apps_dict.items():
        migrations_module, _ = _ensure_migrations_package(label, app_config)
        app_config["migrations"] = migrations_module

    config_dict = tortoise_config.to_dict()
    config_dict["apps"] = apps_dict

    async with tortoise_cli_context(config_dict) as ctx:
        if not ctx.apps:
            raise utils.CLIError("Tortoise apps are not initialized")
        autodetector = MigrationAutodetector(ctx.apps, apps_dict)
        if empty:
            await autodetector.loader.build_graph()
            old_state = await autodetector._project_state()
            new_state = autodetector._current_state()
            writers = []
            for label, app_config in apps_dict.items():
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
        print(f"{_DIM}No changes detected{_RESET}")
        return

    for writer in writers:
        if name:
            try:
                number = int(writer.name.split("_", 1)[0])
            except ValueError:
                number = 1
            writer.name = format_migration_name(number, name)
        path = writer.write()
        print(f"  {_GREEN}Created{_RESET} {writer.app_label}.{writer.name}")
        print(f"    {_DIM}{path}{_RESET}")


def _progress_reporter(event: str, app_label: str, name: str) -> None:
    """Inline progress reporter for migration execution."""
    label = f"{app_label}.{name}"
    if event == "apply_start":
        print(f"  Applying {_CYAN}{label}{_RESET}...", end="", flush=True)
    elif event == "apply_done":
        print(f" {_GREEN}OK{_RESET}")
    elif event == "rollback_start":
        print(f"  Rolling back {_YELLOW}{label}{_RESET}...", end="", flush=True)
    elif event == "rollback_done":
        print(f" {_GREEN}OK{_RESET}")


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

    config = _load_config(ctx)

    target = target_override
    if target is None:
        if app_label and not migration:
            target = f"{app_label}.__latest__"
        elif migration:
            if not app_label:
                raise utils.CLIUsageError("MIGRATION requires APP_LABEL")
            target = f"{app_label}.{migration}"

    async with tortoise_cli_context(config):
        await migrate_api(
            config=config,
            app_labels=None,
            target=target,
            fake=fake,
            dry_run=dry_run,
            direction=direction,
            reporter=_emit_migration_plan,
            progress=_progress_reporter,
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
    tortoise_config = _load_config(ctx)
    apps_config = _select_apps(tortoise_config, app_labels or None)
    apps_dict = {label: app.to_dict() for label, app in apps_config.items()}
    apps_by_connection = _group_apps_by_connection(apps_dict)

    config_dict = tortoise_config.to_dict()
    config_dict["apps"] = apps_dict

    async with tortoise_cli_context(config_dict):
        for connection_name, subset in apps_by_connection.items():
            recorder = MigrationRecorder(get_connection(connection_name))
            applied = await recorder.applied_migrations()
            _emit_history(applied, connection_name, subset)


async def heads(ctx: CLIContext, app_labels: tuple[str, ...]) -> None:
    tortoise_config = _load_config(ctx)
    apps_config = _select_apps(tortoise_config, app_labels or None)
    apps_dict = {label: app.to_dict() for label, app in apps_config.items()}
    apps_by_connection = _group_apps_by_connection(apps_dict)

    loader = MigrationLoader(apps_dict, _NoopRecorder(), load=False)
    await loader.build_graph()

    for connection_name, subset in apps_by_connection.items():
        _emit_heads(loader, connection_name, subset)


async def sqlmigrate_cmd(
    ctx: CLIContext,
    app_label: str,
    migration_name: str,
    backward: bool,
) -> None:
    config = _load_config(ctx)
    try:
        statements = await sqlmigrate_api(
            config=config,
            app_label=app_label,
            migration_name=migration_name,
            backward=backward,
        )
    except ValueError as exc:
        raise utils.CLIError(str(exc)) from None

    if not statements:
        print(f"{_DIM}-- (no SQL statements){_RESET}")
        return

    config_dict = config.to_dict()
    app_cfg = config_dict.get("apps", {}).get(app_label, {})
    connection_name = app_cfg.get("default_connection", "default")
    connection_url = config_dict.get("connections", {}).get(connection_name, "")
    if isinstance(connection_url, dict):
        engine = connection_url.get("engine", "")
        supports_transactional_ddl = "postgres" in engine or "psycopg" in engine
    else:
        supports_transactional_ddl = "postgres" in str(connection_url) or "psycopg" in str(
            connection_url
        )

    wrap_in_transaction = supports_transactional_ddl

    if wrap_in_transaction:
        print(f"{_DIM}BEGIN;{_RESET}")

    for statement in statements:
        if statement.startswith("--"):
            print(f"{_DIM}{statement}{_RESET}")
        else:
            if not statement.rstrip().endswith(";"):
                print(f"{statement};")
            else:
                print(statement)

    if wrap_in_transaction:
        print(f"{_DIM}COMMIT;{_RESET}")


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
    shell_parser = subparsers.add_parser(
        "shell", help="Start an interactive shell (requires ipython or ptpython)."
    )
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


def _add_sqlmigrate_parser(subparsers: argparse._SubParsersAction) -> None:
    sqlmigrate_parser = subparsers.add_parser("sqlmigrate", help="Print the SQL for a migration.")
    sqlmigrate_parser.add_argument("app_label", help="App label.")
    sqlmigrate_parser.add_argument("migration_name", help="Migration name.")
    sqlmigrate_parser.add_argument(
        "--backward",
        action="store_true",
        help="Generate SQL to unapply the migration.",
    )
    sqlmigrate_parser.set_defaults(func=_run_sqlmigrate)


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
    _add_sqlmigrate_parser(subparsers)

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


async def _run_sqlmigrate(ctx: CLIContext, args: argparse.Namespace) -> None:
    await sqlmigrate_cmd(ctx, args.app_label, args.migration_name, args.backward)


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
