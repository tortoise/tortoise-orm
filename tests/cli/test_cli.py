from __future__ import annotations

import contextlib
import datetime as dt
import importlib
import io
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from tortoise.cli import cli as cli_module
from tortoise.config import TortoiseConfig
from tortoise.migrations.autodetector import MigrationAutodetector
from tortoise.migrations.graph import MigrationKey
from tortoise.migrations.writer import MigrationWriter


def _write_package(tmp_path: Path, name: str) -> Path:
    pkg = tmp_path / name
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "models.py").write_text("", encoding="utf-8")
    return pkg


def _write_migrations(pkg: Path, migration_names: list[str]) -> None:
    migrations = pkg / "migrations"
    migrations.mkdir()
    (migrations / "__init__.py").write_text("", encoding="utf-8")
    for name in migration_names:
        (migrations / f"{name}.py").write_text(
            """
from tortoise.migrations.migration import Migration


class Migration(Migration):
    pass
""".lstrip(),
            encoding="utf-8",
        )


def _write_settings(tmp_path: Path, content: str, module_name: str) -> str:
    (tmp_path / f"{module_name}.py").write_text(content, encoding="utf-8")
    return module_name


async def _run_cli(args: list[str]) -> SimpleNamespace:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        exit_code = await cli_module.run_cli_async(args)
    return SimpleNamespace(exit_code=exit_code, output=stdout.getvalue() + stderr.getvalue())


@pytest.mark.asyncio
async def test_init_creates_migrations_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_package(tmp_path, "cli_app")
    module_name = _write_settings(
        tmp_path,
        """
TORTOISE_ORM = {
    "connections": {"default": "sqlite://:memory:"},
    "apps": {
        "app": {"models": ["cli_app.models"], "default_connection": "default"},
    },
}
""".lstrip(),
        f"cli_settings_{tmp_path.name}",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()

    result = await _run_cli(["-c", f"{module_name}.TORTOISE_ORM", "init"])
    assert result.exit_code == 0

    migrations_path = tmp_path / "cli_app" / "migrations"
    assert migrations_path.exists()
    assert (migrations_path / "__init__.py").exists()
    assert "cli_app.migrations" in result.output


@pytest.mark.asyncio
async def test_init_top_level_migrations_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_package(tmp_path, "cli_app")
    module_name = _write_settings(
        tmp_path,
        """
TORTOISE_ORM = {
    "connections": {"default": "sqlite://:memory:"},
    "apps": {
        "app": {
            "models": ["cli_app.models"],
            "default_connection": "default",
            "migrations": "migrations",
        },
    },
}
""".lstrip(),
        f"cli_settings_{tmp_path.name}",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()

    result = await _run_cli(["-c", f"{module_name}.TORTOISE_ORM", "init"])
    assert result.exit_code == 0

    migrations_path = tmp_path / "migrations"
    assert migrations_path.exists()
    assert (migrations_path / "__init__.py").exists()
    assert "migrations" in result.output


@pytest.mark.asyncio
async def test_migrate_passes_target(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _write_package(tmp_path, "cli_app")
    module_name = _write_settings(
        tmp_path,
        """
TORTOISE_ORM = {
    "connections": {"default": "sqlite://:memory:"},
    "apps": {
        "app": {"models": ["cli_app.models"], "default_connection": "default"},
    },
}
""".lstrip(),
        f"cli_settings_{tmp_path.name}",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()

    called: dict[str, Any] = {}

    async def fake_migrate(**kwargs) -> None:
        called.update(kwargs)

    monkeypatch.setattr(cli_module, "migrate_api", fake_migrate)

    result = await _run_cli(["-c", f"{module_name}.TORTOISE_ORM", "migrate", "app", "0001_initial"])
    assert result.exit_code == 0
    assert called["target"] == "app.0001_initial"
    assert called["direction"] == "both"
    assert called["app_labels"] is None


@pytest.mark.asyncio
async def test_migrate_accepts_dotted_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_package(tmp_path, "cli_app")
    module_name = _write_settings(
        tmp_path,
        """
TORTOISE_ORM = {
    "connections": {"default": "sqlite://:memory:"},
    "apps": {
        "app": {"models": ["cli_app.models"], "default_connection": "default"},
    },
}
""".lstrip(),
        f"cli_settings_{tmp_path.name}",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()

    called: dict[str, object] = {}

    async def fake_migrate(**kwargs) -> None:
        called.update(kwargs)

    monkeypatch.setattr(cli_module, "migrate_api", fake_migrate)

    result = await _run_cli(["-c", f"{module_name}.TORTOISE_ORM", "migrate", "app.0001_initial"])
    assert result.exit_code == 0
    assert called["target"] == "app.0001_initial"
    assert called["direction"] == "both"
    assert called["app_labels"] is None


@pytest.mark.asyncio
async def test_upgrade_alias(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module_name = _write_settings(
        tmp_path,
        """
TORTOISE_ORM = {
    "connections": {"default": "sqlite://:memory:"},
    "apps": {
        "app": {"models": ["cli_app.models"], "default_connection": "default"},
    },
}
""".lstrip(),
        f"cli_settings_{tmp_path.name}",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()

    called: dict[str, object] = {}

    async def fake_migrate(**kwargs) -> None:
        called.update(kwargs)

    monkeypatch.setattr(cli_module, "migrate_api", fake_migrate)

    result = await _run_cli(["-c", f"{module_name}.TORTOISE_ORM", "upgrade", "app"])
    assert result.exit_code == 0
    assert called["app_labels"] is None
    assert called["target"] == "app.__latest__"
    assert called["direction"] == "forward"


@pytest.mark.asyncio
async def test_downgrade_defaults_to_first(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module_name = _write_settings(
        tmp_path,
        """
TORTOISE_ORM = {
    "connections": {"default": "sqlite://:memory:"},
    "apps": {
        "app": {"models": ["cli_app.models"], "default_connection": "default"},
    },
}
""".lstrip(),
        f"cli_settings_{tmp_path.name}",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()

    called: dict[str, object] = {}

    async def fake_migrate(**kwargs) -> None:
        called.update(kwargs)

    monkeypatch.setattr(cli_module, "migrate_api", fake_migrate)

    result = await _run_cli(["-c", f"{module_name}.TORTOISE_ORM", "downgrade", "app"])
    assert result.exit_code == 0
    assert called["target"] == "app.__first__"
    assert called["direction"] == "backward"
    assert called["app_labels"] is None


@pytest.mark.asyncio
async def test_downgrade_keeps_full_config_for_dependencies(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _write_package(tmp_path, "cli_accounts")
    _write_package(tmp_path, "cli_orders")
    module_name = _write_settings(
        tmp_path,
        """
TORTOISE_ORM = {
    "connections": {"default": "sqlite://:memory:"},
    "apps": {
        "accounts": {"models": ["cli_accounts.models"], "default_connection": "default"},
        "orders": {"models": ["cli_orders.models"], "default_connection": "default"},
    },
}
""".lstrip(),
        f"cli_settings_{tmp_path.name}",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()

    called: dict[str, object] = {}

    async def fake_migrate(**kwargs) -> None:
        called.update(kwargs)

    monkeypatch.setattr(cli_module, "migrate_api", fake_migrate)

    result = await _run_cli(["-c", f"{module_name}.TORTOISE_ORM", "downgrade", "orders"])
    assert result.exit_code == 0
    assert called["target"] == "orders.__first__"
    assert called["direction"] == "backward"
    assert called["app_labels"] is None
    called_config = called["config"]
    if isinstance(called_config, dict):
        apps = called_config["apps"]
    else:
        assert isinstance(called_config, TortoiseConfig)
        apps = called_config.apps
    assert set(apps.keys()) == {"accounts", "orders"}


@pytest.mark.asyncio
async def test_history_grouped_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_package(tmp_path, "cli_app")
    _write_package(tmp_path, "cli_other")
    module_name = _write_settings(
        tmp_path,
        """
TORTOISE_ORM = {
    "connections": {"default": "sqlite://:memory:"},
    "apps": {
        "app": {"models": ["cli_app.models"], "default_connection": "default"},
        "other": {"models": ["cli_other.models"], "default_connection": "default"},
    },
}
""".lstrip(),
        f"cli_settings_{tmp_path.name}",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()

    async def fake_init(**_kwargs) -> None:
        return None

    async def fake_applied(self) -> list[MigrationKey]:
        return [
            MigrationKey(app_label="app", name="0001_initial"),
            MigrationKey(app_label="other", name="0001_initial"),
        ]

    monkeypatch.setattr(cli_module.Tortoise, "init", fake_init)
    monkeypatch.setattr(cli_module.MigrationRecorder, "applied_migrations", fake_applied)
    monkeypatch.setattr(cli_module, "get_connection", lambda _name: object())

    result = await _run_cli(["-c", f"{module_name}.TORTOISE_ORM", "history"])
    assert result.exit_code == 0
    assert "Connection: default" in result.output
    assert "app:" in result.output
    assert "other:" in result.output
    assert "app 0001_initial" in result.output
    assert "other 0001_initial" in result.output


@pytest.mark.asyncio
async def test_heads_grouped_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app_pkg = _write_package(tmp_path, "cli_app")
    other_pkg = _write_package(tmp_path, "cli_other")
    _write_migrations(app_pkg, ["0001_initial"])
    _write_migrations(other_pkg, ["0001_initial", "0002_more"])

    module_name = _write_settings(
        tmp_path,
        """
TORTOISE_ORM = {
    "connections": {"default": "sqlite://:memory:"},
    "apps": {
        "app": {
            "models": ["cli_app.models"],
            "default_connection": "default",
            "migrations": "cli_app.migrations",
        },
        "other": {
            "models": ["cli_other.models"],
            "default_connection": "default",
            "migrations": "cli_other.migrations",
        },
    },
}
""".lstrip(),
        f"cli_settings_{tmp_path.name}",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()
    sys.modules.pop("cli_other", None)
    sys.modules.pop("cli_other.migrations", None)
    sys.modules.pop("cli_app", None)
    sys.modules.pop("cli_app.migrations", None)
    importlib.import_module("cli_app.migrations")
    importlib.import_module("cli_other.migrations")

    result = await _run_cli(["-c", f"{module_name}.TORTOISE_ORM", "heads"])
    assert result.exit_code == 0
    assert "Connection: default" in result.output
    assert "app:" in result.output
    assert "other:" in result.output
    assert "app.0001_initial" in result.output
    assert "other.0001_initial" in result.output
    assert "other.0002_more" in result.output


@pytest.mark.asyncio
async def test_downgrade_requires_app_label(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module_name = _write_settings(
        tmp_path,
        """
TORTOISE_ORM = {
    "connections": {"default": "sqlite://:memory:"},
    "apps": {
        "app": {"models": ["cli_app.models"], "default_connection": "default"},
    },
}
""".lstrip(),
        f"cli_settings_{tmp_path.name}",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()

    result = await _run_cli(["-c", f"{module_name}.TORTOISE_ORM", "downgrade"])
    assert result.exit_code != 0
    assert "required: app_label" in result.output


@pytest.mark.asyncio
async def test_downgrade_accepts_dotted_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_package(tmp_path, "cli_app")
    module_name = _write_settings(
        tmp_path,
        """
TORTOISE_ORM = {
    "connections": {"default": "sqlite://:memory:"},
    "apps": {
        "app": {"models": ["cli_app.models"], "default_connection": "default"},
    },
}
""".lstrip(),
        f"cli_settings_{tmp_path.name}",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()

    called: dict[str, object] = {}

    async def fake_migrate(**kwargs) -> None:
        called.update(kwargs)

    monkeypatch.setattr(cli_module, "migrate_api", fake_migrate)

    result = await _run_cli(["-c", f"{module_name}.TORTOISE_ORM", "downgrade", "app.0001_initial"])
    assert result.exit_code == 0
    assert called["target"] == "app.0001_initial"
    assert called["direction"] == "backward"
    assert called["app_labels"] is None


@pytest.mark.asyncio
async def test_makemigrations_writes_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_package(tmp_path, "cli_app")
    module_name = _write_settings(
        tmp_path,
        """
TORTOISE_ORM = {
    "connections": {"default": "sqlite://:memory:"},
    "apps": {
        "app": {"models": ["cli_app.models"], "default_connection": "default"},
    },
}
""".lstrip(),
        f"cli_settings_{tmp_path.name}",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()
    sys.modules.pop("cli_app", None)
    sys.modules.pop("cli_app.migrations", None)

    async def fake_init(**_kwargs) -> None:
        return None

    class FakeAutodetector:
        def __init__(self, _apps, apps_config, **_kwargs) -> None:
            self.apps_config = apps_config

        async def changes(self) -> list[MigrationWriter]:
            return [
                MigrationWriter(
                    "0001_initial",
                    "app",
                    [],
                    migrations_module=self.apps_config["app"]["migrations"],
                )
            ]

    monkeypatch.setattr(cli_module.Tortoise, "init", fake_init)
    monkeypatch.setattr(cli_module.Tortoise, "apps", object(), raising=False)
    monkeypatch.setattr(cli_module, "MigrationAutodetector", FakeAutodetector)

    result = await _run_cli(
        ["-c", f"{module_name}.TORTOISE_ORM", "makemigrations", "--name", "add blog"]
    )
    assert result.exit_code == 0

    migrations_path = tmp_path / "cli_app" / "migrations"
    assert (migrations_path / "0001_add_blog.py").exists()


@pytest.mark.asyncio
async def test_makemigrations_no_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_package(tmp_path, "cli_app")
    module_name = _write_settings(
        tmp_path,
        """
TORTOISE_ORM = {
    "connections": {"default": "sqlite://:memory:"},
    "apps": {
        "app": {"models": ["cli_app.models"], "default_connection": "default"},
    },
}
""".lstrip(),
        f"cli_settings_{tmp_path.name}",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()
    sys.modules.pop("cli_app", None)
    sys.modules.pop("cli_app.migrations", None)

    async def fake_init(**_kwargs) -> None:
        return None

    class FakeAutodetector:
        def __init__(self, _apps, _apps_config, **_kwargs) -> None:
            return None

        async def changes(self) -> list[MigrationWriter]:
            return []

    monkeypatch.setattr(cli_module.Tortoise, "init", fake_init)
    monkeypatch.setattr(cli_module.Tortoise, "apps", object(), raising=False)
    monkeypatch.setattr(cli_module, "MigrationAutodetector", FakeAutodetector)

    result = await _run_cli(["-c", f"{module_name}.TORTOISE_ORM", "makemigrations"])
    assert result.exit_code == 0
    assert "No changes detected" in result.output


@pytest.mark.asyncio
async def test_makemigrations_empty_requires_app_label(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_package(tmp_path, "cli_app")
    module_name = _write_settings(
        tmp_path,
        """
TORTOISE_ORM = {
    "connections": {"default": "sqlite://:memory:"},
    "apps": {
        "app": {"models": ["cli_app.models"], "default_connection": "default"},
    },
}
""".lstrip(),
        f"cli_settings_{tmp_path.name}",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()

    result = await _run_cli(["-c", f"{module_name}.TORTOISE_ORM", "makemigrations", "--empty"])
    assert result.exit_code != 0
    assert "--empty requires at least one APP_LABEL" in result.output


@pytest.mark.asyncio
async def test_makemigrations_empty_writes_dependencies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pkg = _write_package(tmp_path, "cli_app")
    _write_migrations(pkg, ["0001_initial", "0002_second"])
    module_name = _write_settings(
        tmp_path,
        """
TORTOISE_ORM = {
    "connections": {"default": "sqlite://:memory:"},
    "apps": {
        "app": {
            "models": ["cli_app.models"],
            "default_connection": "default",
            "migrations": "cli_app.migrations",
        },
    },
}
""".lstrip(),
        f"cli_settings_{tmp_path.name}",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()
    sys.modules.pop("cli_app", None)
    sys.modules.pop("cli_app.migrations", None)

    async def fake_init(**_kwargs) -> None:
        return None

    class FixedAutodetector(MigrationAutodetector):
        def __init__(self, apps, apps_config, **_kwargs) -> None:
            super().__init__(apps, apps_config, now=lambda: dt.datetime(2024, 1, 2, 3, 4))

    monkeypatch.setattr(cli_module.Tortoise, "init", fake_init)
    monkeypatch.setattr(cli_module.Tortoise, "apps", {"app": {}}, raising=False)
    monkeypatch.setattr(cli_module, "MigrationAutodetector", FixedAutodetector)

    result = await _run_cli(
        ["-c", f"{module_name}.TORTOISE_ORM", "makemigrations", "--empty", "app"]
    )
    assert result.exit_code == 0

    migrations_path = tmp_path / "cli_app" / "migrations"
    migration_file = migrations_path / "0003_auto_20240102_0304.py"
    assert migration_file.exists()
    content = migration_file.read_text(encoding="utf-8")
    assert "operations = [" in content
    assert "dependencies = [('app', '0001_initial'), ('app', '0002_second')]" in content


@pytest.mark.asyncio
async def test_makemigrations_empty_respects_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pkg = _write_package(tmp_path, "cli_app")
    _write_migrations(pkg, ["0001_initial", "0002_second"])
    module_name = _write_settings(
        tmp_path,
        """
TORTOISE_ORM = {
    "connections": {"default": "sqlite://:memory:"},
    "apps": {
        "app": {
            "models": ["cli_app.models"],
            "default_connection": "default",
            "migrations": "cli_app.migrations",
        },
    },
}
""".lstrip(),
        f"cli_settings_{tmp_path.name}",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()
    sys.modules.pop("cli_app", None)
    sys.modules.pop("cli_app.migrations", None)

    async def fake_init(**_kwargs) -> None:
        return None

    class FixedAutodetector(MigrationAutodetector):
        def __init__(self, apps, apps_config, **_kwargs) -> None:
            super().__init__(apps, apps_config, now=lambda: dt.datetime(2024, 1, 2, 3, 4))

    monkeypatch.setattr(cli_module.Tortoise, "init", fake_init)
    monkeypatch.setattr(cli_module.Tortoise, "apps", {"app": {}}, raising=False)
    monkeypatch.setattr(cli_module, "MigrationAutodetector", FixedAutodetector)

    result = await _run_cli(
        [
            "-c",
            f"{module_name}.TORTOISE_ORM",
            "makemigrations",
            "--empty",
            "--name",
            "manual",
            "app",
        ]
    )
    assert result.exit_code == 0

    migrations_path = tmp_path / "cli_app" / "migrations"
    assert (migrations_path / "0003_manual.py").exists()
