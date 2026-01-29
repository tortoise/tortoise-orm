from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from collections.abc import Iterable
from pathlib import Path
from types import ModuleType
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomlkit as tomllib


class CLIError(Exception):
    pass


class CLIUsageError(CLIError):
    pass


def tortoise_orm_config(file: str = "pyproject.toml") -> str:
    """
    Get tortoise orm config from env or pyproject.toml.

    :param file: toml file that contains tool.tortoise settings
    :return: module path and var name that stores the tortoise config
    """
    if not (config := os.getenv("TORTOISE_ORM", "")) and (p := Path(file)).exists():
        doc = tomllib.loads(p.read_text("utf-8"))
        config = doc.get("tool", {}).get("tortoise", {}).get("tortoise_orm", "")
    return config


def get_tortoise_config(config: str) -> dict[str, Any]:
    """
    Get tortoise config from module path.

    :param config: module path + var name, e.g. "settings.TORTOISE_ORM"
    """
    splits = config.split(".")
    config_path = ".".join(splits[:-1])
    tortoise_config = splits[-1]

    try:
        config_module = importlib.import_module(config_path)
    except ModuleNotFoundError as exc:
        raise CLIError(f"Error while importing configuration module: {exc}") from None

    config_value = getattr(config_module, tortoise_config, None)
    if not config_value:
        raise CLIUsageError(f'Can\'t get "{tortoise_config}" from module "{config_module}"')
    return config_value


def _first_models_module(models: Iterable[ModuleType | str] | str | None) -> str | None:
    if isinstance(models, str):
        return models
    if not models:
        return None
    for item in models:
        if isinstance(item, str):
            return item
        if isinstance(item, ModuleType):
            return item.__name__
    return None


def infer_migrations_module(models: Iterable[ModuleType | str] | str | None) -> str | None:
    module = _first_models_module(models)
    if not module:
        return None
    if module.endswith(".models"):
        base = module[: -len(".models")]
    elif "." in module:
        base = module.rsplit(".", 1)[0]
    else:
        base = module
    return f"{base}.migrations"


def normalize_apps_config(apps_config: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    normalized: dict[str, dict[str, Any]] = {}
    for label, config in apps_config.items():
        updated = dict(config)
        if "migrations" not in updated:
            inferred = infer_migrations_module(updated.get("models"))
            if inferred and importlib.util.find_spec(inferred) is not None:
                updated["migrations"] = inferred
        normalized[label] = updated
    return normalized
