import importlib
from pathlib import Path
from types import ModuleType

import pytest

from tortoise.cli import utils

EMPTY_TORTOISE_ORM = None


def test_tortoise_orm_config_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TORTOISE_ORM", "app.settings.TORTOISE_ORM")
    assert utils.tortoise_orm_config() == "app.settings.TORTOISE_ORM"


def test_tortoise_orm_config_pyproject(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.tortoise]
tortoise_orm = "settings.TORTOISE_ORM"
""".lstrip(),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TORTOISE_ORM", raising=False)
    assert utils.tortoise_orm_config() == "settings.TORTOISE_ORM"


def test_tortoise_orm_config_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TORTOISE_ORM", raising=False)
    assert utils.tortoise_orm_config() == ""


def test_get_tortoise_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module_name = f"cli_settings_{tmp_path.name}"
    settings = tmp_path / f"{module_name}.py"
    settings.write_text("TORTOISE_ORM = {'connections': {}, 'apps': {}}\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()
    import sys

    sys.modules.pop("cli_app", None)
    sys.modules.pop("cli_app.migrations", None)

    assert utils.get_tortoise_config(f"{module_name}.TORTOISE_ORM") == {
        "connections": {},
        "apps": {},
    }

    with pytest.raises(
        utils.CLIError,
        match="Error while importing configuration module: No module named 'missing'",
    ):
        utils.get_tortoise_config("missing.TORTOISE_ORM")

    with pytest.raises(utils.CLIUsageError):
        utils.get_tortoise_config(f"{module_name}.MISSING")


def test_infer_migrations_module() -> None:
    module = ModuleType("demo.models")
    assert utils.infer_migrations_module([module]) == "demo.migrations"
    assert utils.infer_migrations_module(["demo.models"]) == "demo.migrations"
    assert utils.infer_migrations_module(["demo.sub.models"]) == "demo.sub.migrations"
    assert utils.infer_migrations_module(["demo.other"]) == "demo.migrations"
    assert utils.infer_migrations_module(None) is None


def test_normalize_apps_config_infers_migrations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app_dir = tmp_path / "cli_app"
    app_dir.mkdir()
    (app_dir / "__init__.py").write_text("", encoding="utf-8")
    (app_dir / "models.py").write_text("", encoding="utf-8")
    migrations_dir = app_dir / "migrations"
    migrations_dir.mkdir()
    (migrations_dir / "__init__.py").write_text("", encoding="utf-8")

    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()
    import sys

    sys.modules.pop("cli_app_no_migrations", None)
    sys.modules.pop("cli_app_no_migrations.migrations", None)
    apps = {
        "app": {
            "models": ["cli_app.models"],
            "default_connection": "default",
        }
    }
    normalized = utils.normalize_apps_config(apps)
    assert normalized["app"]["migrations"] == "cli_app.migrations"


def test_normalize_apps_config_skips_missing_module(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app_dir = tmp_path / "cli_app_no_migrations"
    app_dir.mkdir()
    (app_dir / "__init__.py").write_text("", encoding="utf-8")
    (app_dir / "models.py").write_text("", encoding="utf-8")

    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()
    apps = {
        "app": {
            "models": ["cli_app_no_migrations.models"],
            "default_connection": "default",
        }
    }
    normalized = utils.normalize_apps_config(apps)
    assert "migrations" not in normalized["app"]
