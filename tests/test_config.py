"""
Tests for tortoise.config module - TortoiseConfig class.
"""

import shutil
from pathlib import Path

import orjson
import pytest
import yaml

from tortoise.backends.base.config_generator import expand_db_url
from tortoise.config import AppConfig, DBUrlConfig, TortoiseConfig
from tortoise.exceptions import ConfigurationError


class TestTortoiseConfig:
    @pytest.fixture
    def db_url(self) -> str:
        return "sqlite://db.sqlite3"

    @pytest.fixture
    def simple_config(self, db_url: str) -> dict:
        return {
            "connections": {"default": db_url},
            "apps": {
                "app": {
                    "models": ["app.models"],
                    "default_connection": "default",
                }
            },
        }

    @pytest.mark.parametrize(
        "config,msg",
        [
            ([], "TortoiseConfig must be created from a mapping"),
            ({}, 'Config must define "connections" section'),
            ({"connections": ""}, 'Config must define "apps" section'),
            ({"connections": "", "apps": ""}, 'Config "connections" must be a mapping'),
            (
                {"connections": {"default": []}, "apps": ""},
                "Connection values must be mapping or string",
            ),
            (
                {"connections": {"default": ""}, "apps": ""},
                "DBUrlConfig.url must be a non-empty string",
            ),
            (
                {"connections": {"default": "db.sqlite3"}, "apps": ""},
                'Config "apps" must be a mapping',
            ),
            (
                {"connections": {"default": "db.sqlite3"}, "apps": {"auth": ""}},
                "App values must be mappings",
            ),
            (
                {"connections": {"default": "db.sqlite3"}, "apps": {"auth": {}}, "routers": {}},
                'AppConfig requires "models"',
            ),
            (
                {
                    "connections": {"default": "db.sqlite3"},
                    "apps": {"auth": {"models": []}},
                    "routers": {},
                },
                "AppConfig.models must be a non-empty list of strings",
            ),
            (
                {
                    "connections": {"default": "db.sqlite3"},
                    "apps": {"auth": {"models": ["models"]}},
                    "routers": "",
                },
                "TortoiseConfig.routers must be a list or None",
            ),
        ],
    )
    def test_from_invalid_dict(self, config: list | dict, msg: str):
        with pytest.raises(ConfigurationError, match=msg):
            TortoiseConfig.from_dict(config)  # type: ignore

    def test_from_dict(self, simple_config: dict):
        assert TortoiseConfig.from_dict(simple_config) == TortoiseConfig(
            connections={"default": DBUrlConfig(url="sqlite://db.sqlite3")},
            apps={
                "app": AppConfig(
                    models=["app.models"], default_connection="default", migrations=None
                )
            },
            routers=None,
            use_tz=None,
            timezone=None,
        )
        full = {
            "connections": {
                "default": "sqlite://db.sqlite3",
                "second": "sqlite://db2.sqlite3",
            },
            "apps": {
                "app1": {
                    "models": ["app1.models"],
                    "migrations": "app1.migrations",
                },
                "app2": {
                    "models": ["app2.models"],
                    "default_connection": "second",
                    "migrations": "app2.migrations",
                },
            },
            "routers": ["path.Router"],
            "use_tz": True,
            "timezone": "UTC",
        }
        assert TortoiseConfig.from_dict(full) == TortoiseConfig(
            connections={
                "default": DBUrlConfig(url="sqlite://db.sqlite3"),
                "second": DBUrlConfig(url="sqlite://db2.sqlite3"),
            },
            apps={
                "app1": AppConfig(
                    models=["app1.models"], default_connection=None, migrations="app1.migrations"
                ),
                "app2": AppConfig(
                    models=["app2.models"],
                    default_connection="second",
                    migrations="app2.migrations",
                ),
            },
            routers=["path.Router"],
            use_tz=True,
            timezone="UTC",
        )

    def test_from_config_file(self, tmp_path: Path, simple_config: dict):
        file = tmp_path / "tortoise_conf.json"
        file.write_bytes(orjson.dumps(simple_config))
        filename: str = file.as_posix()
        assert (
            TortoiseConfig.from_config_file(file)
            == TortoiseConfig.from_config_file(filename)
            == TortoiseConfig.from_dict(simple_config)
            == TortoiseConfig.resolve_args(config_file=file)
        )

        yaml_file = file.with_suffix(".yml")
        with yaml_file.open("w") as f:
            yaml.safe_dump(simple_config, f, default_flow_style=False)
        yaml_file_2 = file.with_suffix(".yaml")
        shutil.copy(yaml_file, yaml_file_2)
        assert (
            TortoiseConfig.from_config_file(yaml_file)
            == TortoiseConfig.from_config_file(str(yaml_file))
            == TortoiseConfig.from_config_file(yaml_file_2)
            == TortoiseConfig.from_config_file(file)
            == TortoiseConfig.resolve_args(config_file=yaml_file)
        )

    def test_from_db_url_and_modules(self, simple_config: dict, db_url: str):
        modules = {"app": simple_config["apps"]["app"]["models"]}
        typed_config = TortoiseConfig.from_db_url_and_modules(db_url, modules)
        assert typed_config == TortoiseConfig.resolve_args(db_url=db_url, modules=modules)
        assert typed_config.apps == TortoiseConfig.from_dict(simple_config).apps

    @pytest.mark.parametrize(
        "config,msg",
        [
            ({}, "Must provide either 'config', 'config_file', or both 'db_url' and 'modules'"),
            (
                dict(db_url=""),
                "Must provide either 'config', 'config_file', or both 'db_url' and 'modules'",
            ),
            (
                dict(config={}, config_file="a.json"),
                "Cannot specify both 'config' and 'config_file'",
            ),
        ],
    )
    def test_resolve_args_invalid(self, config: dict, msg: str):
        with pytest.raises(ConfigurationError, match=msg):
            TortoiseConfig.resolve_args(**config)

    def test_resolve_args(self, tmp_path: Path, db_url: str, simple_config: dict):
        config_file = tmp_path / "config.json"
        config_file.write_bytes(orjson.dumps(simple_config))
        typed_config = TortoiseConfig.resolve_args(simple_config)
        assert typed_config == TortoiseConfig.resolve_args(config_file=config_file)

        typed_config_2 = TortoiseConfig.resolve_args(db_url=db_url, modules={"app": ["app.models"]})
        assert typed_config.apps == typed_config_2.apps
        assert (
            expand_db_url(str(typed_config.connections["default"].to_config()))
            == typed_config_2.connections["default"].to_config()
        )
