from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from tortoise.exceptions import ConfigurationError


@dataclass(frozen=True)
class DBUrlConfig:
    url: str

    def __post_init__(self) -> None:
        if not isinstance(self.url, str) or not self.url:
            raise ConfigurationError("DBUrlConfig.url must be a non-empty string")

    def to_config(self) -> str:
        return self.url


@dataclass(frozen=True)
class ConnectionConfig:
    engine: str | None = None
    credentials: dict[str, Any] = field(default_factory=dict)
    db_url: str | None = None

    def __post_init__(self) -> None:
        if self.db_url is not None:
            if self.engine is not None or self.credentials:
                raise ConfigurationError(
                    "ConnectionConfig cannot set db_url together with engine/credentials"
                )
            if not isinstance(self.db_url, str) or not self.db_url:
                raise ConfigurationError("ConnectionConfig.db_url must be a non-empty string")
            return

        if self.engine is None or not isinstance(self.engine, str) or not self.engine:
            raise ConfigurationError("ConnectionConfig.engine must be a non-empty string")
        if not isinstance(self.credentials, dict):
            raise ConfigurationError("ConnectionConfig.credentials must be a dict")

    def to_config(self) -> str | dict[str, Any]:
        if self.db_url is not None:
            return self.db_url
        return {"engine": self.engine, "credentials": self.credentials}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ConnectionConfig:
        if not isinstance(data, Mapping):
            raise ConfigurationError("ConnectionConfig must be created from a mapping")
        credentials = data.get("credentials", {})
        if not isinstance(credentials, Mapping):
            raise ConfigurationError("ConnectionConfig.credentials must be a dict")
        return cls(
            engine=data.get("engine"),
            credentials=dict(credentials),
            db_url=data.get("db_url"),
        )


@dataclass(frozen=True)
class AppConfig:
    models: list[str]
    default_connection: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.models, list) or not self.models:
            raise ConfigurationError("AppConfig.models must be a non-empty list of strings")
        for model in self.models:
            if not isinstance(model, str) or not model:
                raise ConfigurationError("AppConfig.models must contain non-empty strings")
        if self.default_connection is not None and not isinstance(self.default_connection, str):
            raise ConfigurationError("AppConfig.default_connection must be a string or None")

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"models": self.models}
        if self.default_connection is not None:
            data["default_connection"] = self.default_connection
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AppConfig:
        if not isinstance(data, Mapping):
            raise ConfigurationError("AppConfig must be created from a mapping")
        if "models" not in data:
            raise ConfigurationError('AppConfig requires "models"')
        if not isinstance(data["models"], list):
            raise ConfigurationError("AppConfig.models must be a list of strings")
        return cls(
            models=list(data["models"]),
            default_connection=data.get("default_connection"),
        )


@dataclass(frozen=True)
class TortoiseConfig:
    connections: dict[str, ConnectionConfig | DBUrlConfig]
    apps: dict[str, AppConfig]
    routers: list[str | type] | None = None
    use_tz: bool | None = None
    timezone: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.connections, dict) or not self.connections:
            raise ConfigurationError("TortoiseConfig.connections must be a non-empty dict")
        for name, conn in self.connections.items():
            if not isinstance(name, str) or not name:
                raise ConfigurationError("Connection names must be non-empty strings")
            if not isinstance(conn, (ConnectionConfig, DBUrlConfig)):
                raise ConfigurationError(
                    "Connection values must be ConnectionConfig or DBUrlConfig"
                )

        if not isinstance(self.apps, dict) or not self.apps:
            raise ConfigurationError("TortoiseConfig.apps must be a non-empty dict")
        for name, app in self.apps.items():
            if not isinstance(name, str) or not name:
                raise ConfigurationError("App names must be non-empty strings")
            if not isinstance(app, AppConfig):
                raise ConfigurationError("App values must be AppConfig")
            if app.default_connection and app.default_connection not in self.connections:
                raise ConfigurationError(
                    f'App "{name}" refers to unknown connection "{app.default_connection}"'
                )

        if self.routers is not None:
            if not isinstance(self.routers, list):
                raise ConfigurationError("TortoiseConfig.routers must be a list or None")
            for router in self.routers:
                if not isinstance(router, (str, type)):
                    raise ConfigurationError("Routers must be str or type")

        if self.use_tz is not None and not isinstance(self.use_tz, bool):
            raise ConfigurationError("TortoiseConfig.use_tz must be a bool or None")

        if self.timezone is not None and not isinstance(self.timezone, str):
            raise ConfigurationError("TortoiseConfig.timezone must be a string or None")

    def to_dict(self) -> dict[str, Any]:
        connections = {name: conn.to_config() for name, conn in self.connections.items()}
        apps = {name: app.to_dict() for name, app in self.apps.items()}
        config: dict[str, Any] = {
            "connections": connections,
            "apps": apps,
        }
        if self.routers is not None:
            config["routers"] = self.routers
        if self.use_tz is not None:
            config["use_tz"] = self.use_tz
        if self.timezone is not None:
            config["timezone"] = self.timezone
        return config

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> TortoiseConfig:
        if not isinstance(data, Mapping):
            raise ConfigurationError("TortoiseConfig must be created from a mapping")

        if "connections" not in data:
            raise ConfigurationError('Config must define "connections" section')
        if "apps" not in data:
            raise ConfigurationError('Config must define "apps" section')

        raw_connections = data["connections"]
        if not isinstance(raw_connections, Mapping):
            raise ConfigurationError('Config "connections" must be a mapping')
        connections: dict[str, ConnectionConfig | DBUrlConfig] = {}
        for name, conn in raw_connections.items():
            if isinstance(conn, str):
                connections[name] = DBUrlConfig(conn)
            elif isinstance(conn, Mapping):
                connections[name] = ConnectionConfig.from_dict(conn)
            else:
                raise ConfigurationError("Connection values must be mapping or string")

        raw_apps = data["apps"]
        if not isinstance(raw_apps, Mapping):
            raise ConfigurationError('Config "apps" must be a mapping')
        apps: dict[str, AppConfig] = {}
        for name, app in raw_apps.items():
            if not isinstance(app, Mapping):
                raise ConfigurationError("App values must be mappings")
            apps[name] = AppConfig.from_dict(app)

        routers = data.get("routers")
        if routers is not None and not isinstance(routers, list):
            if isinstance(routers, str):
                raise ConfigurationError("TortoiseConfig.routers must be a list or None")
            routers = list(routers)

        return cls(
            connections=connections,
            apps=apps,
            routers=routers,
            use_tz=data.get("use_tz"),
            timezone=data.get("timezone"),
        )
