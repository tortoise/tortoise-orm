from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from asyncclick.testing import CliRunner

from tortoise.cli import cli as cli_module
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


@pytest.mark.asyncio
async def test_init_creates_migrations_package(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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

    runner = CliRunner()
    result = await runner.invoke(
        cli_module.cli, ["-c", f"{module_name}.TORTOISE_ORM", "init"]
    )
    assert result.exit_code == 0

    migrations_path = tmp_path / "cli_app" / "migrations"
    assert migrations_path.exists()
    assert (migrations_path / "__init__.py").exists()
    assert "cli_app.migrations" in result.output


@pytest.mark.asyncio
async def test_init_top_level_migrations_package(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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

    runner = CliRunner()
    result = await runner.invoke(
        cli_module.cli, ["-c", f"{module_name}.TORTOISE_ORM", "init"]
    )
    assert result.exit_code == 0

    migrations_path = tmp_path / "migrations"
    assert migrations_path.exists()
    assert (migrations_path / "__init__.py").exists()
    assert "migrations" in result.output


@pytest.mark.asyncio
async def test_migrate_passes_target(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
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

    runner = CliRunner()
    result = await runner.invoke(
        cli_module.cli,
        ["-c", f"{module_name}.TORTOISE_ORM", "migrate", "app", "0001_initial"],
    )
    assert result.exit_code == 0
    assert called["target"] == "app.0001_initial"
    assert called["app_labels"] == ["app"]


@pytest.mark.asyncio
async def test_migrate_accepts_dotted_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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

    runner = CliRunner()
    result = await runner.invoke(
        cli_module.cli,
        ["-c", f"{module_name}.TORTOISE_ORM", "migrate", "app.0001_initial"],
    )
    assert result.exit_code == 0
    assert called["target"] == "app.0001_initial"
    assert called["app_labels"] == ["app"]


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

    runner = CliRunner()
    result = await runner.invoke(
        cli_module.cli,
        ["-c", f"{module_name}.TORTOISE_ORM", "upgrade", "app"],
    )
    assert result.exit_code == 0
    assert called["app_labels"] == ["app"]
    assert called["target"] is None


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

    runner = CliRunner()
    result = await runner.invoke(
        cli_module.cli,
        ["-c", f"{module_name}.TORTOISE_ORM", "downgrade", "app"],
    )
    assert result.exit_code == 0
    assert called["target"] == "app.__first__"
    assert called["app_labels"] == ["app"]


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
    monkeypatch.setattr(cli_module.connections, "get", lambda _name: object())

    runner = CliRunner()
    result = await runner.invoke(
        cli_module.cli, ["-c", f"{module_name}.TORTOISE_ORM", "history"]
    )
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

    runner = CliRunner()
    result = await runner.invoke(
        cli_module.cli, ["-c", f"{module_name}.TORTOISE_ORM", "heads"]
    )
    assert result.exit_code == 0
    assert "Connection: default" in result.output
    assert "app:" in result.output
    assert "other:" in result.output
    assert "app.0001_initial" in result.output
    assert "other.0001_initial" in result.output
    assert "other.0002_more" in result.output


@pytest.mark.asyncio
async def test_downgrade_requires_app_label(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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

    runner = CliRunner()
    result = await runner.invoke(cli_module.cli, ["-c", f"{module_name}.TORTOISE_ORM", "downgrade"])
    assert result.exit_code != 0
    assert "Missing argument" in result.output


@pytest.mark.asyncio
async def test_downgrade_accepts_dotted_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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

    runner = CliRunner()
    result = await runner.invoke(
        cli_module.cli,
        ["-c", f"{module_name}.TORTOISE_ORM", "downgrade", "app.0001_initial"],
    )
    assert result.exit_code == 0
    assert called["target"] == "app.0001_initial"
    assert called["app_labels"] == ["app"]


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

    runner = CliRunner()
    result = await runner.invoke(
        cli_module.cli, ["-c", f"{module_name}.TORTOISE_ORM", "makemigrations", "--name", "add blog"]
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

    runner = CliRunner()
    result = await runner.invoke(
        cli_module.cli, ["-c", f"{module_name}.TORTOISE_ORM", "makemigrations"]
    )
    assert result.exit_code == 0
    assert "No changes detected" in result.output
