from __future__ import annotations

import importlib
import json
import logging
import os
import warnings
from collections.abc import Callable, Coroutine, Iterable
from types import ModuleType
from typing import Any

from anyio import from_thread

from tortoise.apps import Apps
from tortoise.backends.base.client import BaseDBAsyncClient
from tortoise.backends.base.config_generator import expand_db_url, generate_config
from tortoise.config import TortoiseConfig
from tortoise.connection import connections
from tortoise.exceptions import ConfigurationError
from tortoise.fields.relational import (
    BackwardFKRelation,
    BackwardOneToOneRelation,
    ForeignKeyFieldInstance,
    ManyToManyFieldInstance,
    OneToOneFieldInstance,
)
from tortoise.log import logger
from tortoise.models import Model, ModelMeta
from tortoise.timezone import _reset_timezone_cache
from tortoise.utils import generate_schema_for_client


class Tortoise:
    apps: Apps | None = None
    table_name_generator: Callable[[type[Model]], str] | None = None
    _inited: bool = False

    @classmethod
    def get_connection(cls, connection_name: str) -> BaseDBAsyncClient:
        """
        Returns the connection by name.

        :raises ConfigurationError: If connection name does not exist.

        .. warning::
           This is deprecated and will be removed in a future release. Please use
           :meth:`connections.get<tortoise.connection.ConnectionHandler.get>` instead.
        """
        return connections.get(connection_name)

    @classmethod
    def describe_model(
        cls, model: type[Model], serializable: bool = True
    ) -> dict[str, Any]:  # pragma: nocoverage
        """
        Describes the given list of models or ALL registered models.

        :param model:
            The Model to describe

        :param serializable:
            ``False`` if you want raw python objects,
            ``True`` for JSON-serializable data. (Defaults to ``True``)

        See :meth:`tortoise.models.Model.describe`

        .. warning::
           This is deprecated, please use :meth:`tortoise.models.Model.describe` instead
        """
        warnings.warn(
            "Tortoise.describe_model(<MODEL>) is deprecated, please use <MODEL>.describe() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return model.describe(serializable=serializable)

    @classmethod
    def describe_models(
        cls, models: list[type[Model]] | None = None, serializable: bool = True
    ) -> dict[str, dict[str, Any]]:
        """
        Describes the given list of models or ALL registered models.

        :param models:
            List of models to describe, if not provided then describes ALL registered models

        :param serializable:
            ``False`` if you want raw python objects,
            ``True`` for JSON-serializable data. (Defaults to ``True``)

        :return:
            A dictionary containing the model qualifier as key,
            and the same output as ``describe_model(...)`` as value:

            .. code-block:: python3

                {
                    "models.User": {...},
                    "models.Permission": {...}
                }
        """

        if not models:
            models = []
            if cls.apps:
                models = list(cls.apps.get_models_iterable())

        return {
            f"{model._meta.app}.{model.__name__}": model.describe(serializable) for model in models
        }

    @classmethod
    def _init_relations(cls) -> None:
        if not cls.apps:
            return
        cls.apps._init_relations()

    @classmethod
    def init_models(
        cls,
        models_paths: Iterable[ModuleType | str],
        app_label: str,
        _init_relations: bool = True,
    ) -> None:
        """
        Early initialisation of Tortoise ORM Models.

        Initialise the relationships between Models.
        This does not initialise any database connection.

        :param models_paths: Models paths to initialise
        :param app_label: The app label, e.g. 'models'
        :param _init_relations: Whether to init relations or not

        :raises ConfigurationError: If models are invalid.
        """
        cls.init_app(app_label, models_paths, _init_relations=_init_relations)

    @classmethod
    def init_app(
        cls,
        label: str,
        model_paths: Iterable[ModuleType | str],
        _init_relations: bool = True,
    ) -> dict[str, type[Model]]:
        """
        Early initialization of Tortoise ORM Models for a single app.

        :param label: The app label, e.g. 'models'
        :param model_paths: Models paths to initialize
        :param _init_relations: Whether to init relations or not
        """
        if not cls.apps:
            cls.apps = Apps({}, connections, cls.table_name_generator)
        cls.apps._table_name_generator = cls.table_name_generator
        return cls.apps.init_app(label, model_paths, _init_relations=_init_relations)

    @classmethod
    def _init_apps(
        cls, apps_config: dict[str, dict[str, Any]], *, validate_connections: bool = True
    ) -> None:
        cls.apps = Apps(
            apps_config,
            connections,
            cls.table_name_generator,
            validate_connections=validate_connections,
        )

    @classmethod
    def _get_config_from_config_file(cls, config_file: str) -> dict:
        _, extension = os.path.splitext(config_file)
        if extension in (".yml", ".yaml"):
            import yaml  # pylint: disable=C0415

            with open(config_file) as f:
                config = yaml.safe_load(f)
        elif extension == ".json":
            with open(config_file) as f:
                config = json.load(f)
        else:
            raise ConfigurationError(
                f"Unknown config extension {extension}, only .yml and .json are supported"
            )
        return config

    @classmethod
    def _build_initial_querysets(cls) -> None:
        if cls.apps:
            cls.apps._build_initial_querysets()

    @classmethod
    async def init(
        cls,
        config: dict[str, Any] | TortoiseConfig | None = None,
        config_file: str | None = None,
        _create_db: bool = False,
        db_url: str | None = None,
        modules: dict[str, Iterable[str | ModuleType]] | None = None,
        use_tz: bool = False,
        timezone: str = "UTC",
        routers: list[str | type] | None = None,
        table_name_generator: Callable[[type[Model]], str] | None = None,
        init_connections: bool = True,
    ) -> None:
        """
        Sets up Tortoise-ORM: loads apps and models, configures database connections but does not
        connect to the database yet. The actual connection or connection pool is established
        lazily on first query execution.

        You can configure using only one of ``config``, ``config_file``
        and ``(db_url, modules)``.

        :param config:
            Dict containing config or ``TortoiseConfig``:

            .. admonition:: Example

                .. code-block:: python3

                    {
                        'connections': {
                            # Dict format for connection
                            'default': {
                                'engine': 'tortoise.backends.asyncpg',
                                'credentials': {
                                    'host': 'localhost',
                                    'port': '5432',
                                    'user': 'tortoise',
                                    'password': 'qwerty123',
                                    'database': 'test',
                                }
                            },
                            # Using a DB_URL string
                            'default': 'postgres://postgres:qwerty123@localhost:5432/test'
                        },
                        'apps': {
                            'my_app': {
                                'models': ['__main__'],
                                # If no default_connection specified, defaults to 'default'
                                'default_connection': 'default',
                            }
                        },
                        'routers': ['path.router1', 'path.router2'],
                        'use_tz': False,
                        'timezone': 'UTC'
                    }

        :param config_file:
            Path to .json or .yml (if PyYAML installed) file containing config with
            same format as above.
        :param db_url:
            Use a DB_URL string. See :ref:`db_url`
        :param modules:
            Dictionary of ``key``: [``list_of_modules``] that defined "apps" and modules that
            should be discovered for models.
        :param _create_db:
            If ``True`` tries to create database for specified connections,
            could be used for testing purposes.
        :param use_tz:
            A boolean that specifies if datetime will be timezone-aware by default or not.
        :param timezone:
            Timezone to use, default is UTC.
        :param routers:
            A list of db routers str path or module.
        :param table_name_generator:
            A callable that generates table names. The model class will be passed as its argument.
            If not provided, Tortoise will use the lowercase model name as the table name.
            Example: ``lambda cls: f"prefix_{cls.__name__.lower()}"``
        :param init_connections:
            When ``False``, skips initializing connection clients while still loading apps
            and validating connection names against the config.

        :raises ConfigurationError: For any configuration error
        """
        if cls._inited:
            await connections.close_all(discard=True)
        if int(bool(config) + bool(config_file) + bool(db_url)) != 1:
            raise ConfigurationError(
                'You should init either from "config", "config_file" or "db_url"'
            )

        if config_file:
            config = cls._get_config_from_config_file(config_file)
        elif db_url:
            if not modules:
                raise ConfigurationError('You must specify "db_url" and "modules" together')
            config = generate_config(db_url, modules)
        elif config is None:
            raise ConfigurationError('You must specify "config" or "config_file" or "db_url"')
        elif isinstance(config, TortoiseConfig):
            config = config.to_dict()
        else:
            try:
                TortoiseConfig.from_dict(config)
            except ConfigurationError as exc:
                warnings.warn(
                    f"Config validation warning: {exc}",
                    RuntimeWarning,
                    stacklevel=2,
                )

        try:
            connections_config = config["connections"]
        except KeyError:
            raise ConfigurationError('Config must define "connections" section')

        try:
            apps_config = config["apps"]
        except KeyError:
            raise ConfigurationError('Config must define "apps" section')

        use_tz = config.get("use_tz", use_tz)
        timezone = config.get("timezone", timezone)
        routers = config.get("routers", routers)

        cls.table_name_generator = table_name_generator

        if logger.isEnabledFor(logging.DEBUG):
            str_connection_config = cls.star_password(connections_config)
            logger.debug(
                "Tortoise-ORM startup\n    connections: %s\n    apps: %s",
                str_connection_config,
                str(apps_config),
            )

        cls._init_timezone(use_tz, timezone)
        if not init_connections and _create_db:
            raise ConfigurationError("init_connections=False cannot be used with _create_db=True")
        if init_connections:
            await connections._init(connections_config, _create_db)
        else:
            connections._init_config(connections_config)
        cls._init_apps(apps_config, validate_connections=init_connections)
        cls._init_routers(routers)

        cls._inited = True

    @staticmethod
    def star_password(connections_config) -> str:
        # Mask passwords to hide sensitive information in logs output
        passwords = []
        for name, info in connections_config.items():
            if isinstance(info, str):
                info = expand_db_url(info)
            if password := info.get("credentials", {}).get("password"):
                passwords.append(password)

        str_connection_config = str(connections_config)
        for password in passwords:
            str_connection_config = str_connection_config.replace(
                password,
                # Show one third of the password at beginning (may be better for debugging purposes)
                f"{password[0 : len(password) // 3]}***",
            )
        return str_connection_config

    @classmethod
    def _init_routers(cls, routers: list[str | type] | None = None) -> None:
        from tortoise.router import router

        routers = routers or []
        router_cls = []
        for r in routers:
            if isinstance(r, str):
                try:
                    module_name, class_name = r.rsplit(".", 1)
                    router_cls.append(getattr(importlib.import_module(module_name), class_name))
                except Exception:
                    raise ConfigurationError(f"Can't import router from `{r}`")
            elif isinstance(r, type):
                router_cls.append(r)
            else:
                raise ConfigurationError("Router must be either str or type")
        router.init_routers(router_cls)

    @classmethod
    async def close_connections(cls) -> None:
        """
        Close all connections cleanly.

        It is required for this to be called on exit,
        else your event loop may never complete
        as it is waiting for the connections to die.

        .. warning::
           This is deprecated and will be removed in a future release. Please use
           :meth:`connections.close_all<tortoise.connection.ConnectionHandler.close_all>` instead.
        """
        await connections.close_all()
        logger.info("Tortoise-ORM shutdown")

    @classmethod
    async def _reset_apps(cls) -> None:
        if not cls.apps:
            return

        for model in cls.apps.get_models_iterable():
            if isinstance(model, ModelMeta):
                model._meta.default_connection = None
        cls.apps.clear()
        cls.apps = None

    @classmethod
    async def generate_schemas(cls, safe: bool = True) -> None:
        """
        Generate schemas according to models provided to ``.init()`` method.
        Will fail if schemas already exists, so it's not recommended to be used as part
        of application workflow

        :param safe: When set to true, creates the table only when it does not already exist.

        :raises ConfigurationError: When ``.init()`` has not been called.
        """
        if not cls._inited:
            raise ConfigurationError("You have to call .init() first before generating schemas")
        for connection in connections.all():
            await generate_schema_for_client(connection, safe)

    @classmethod
    async def _drop_databases(cls) -> None:
        """
        Tries to drop all databases provided in config passed to ``.init()`` method.
        Normally should be used only for testing purposes.

        :raises ConfigurationError: When ``.init()`` has not been called.
        """
        if not cls._inited:
            raise ConfigurationError("You have to call .init() first before deleting schemas")
        # this closes any existing connections/pool if any and clears
        # the storage
        await connections.close_all(discard=False)
        for conn in connections.all():
            await conn.db_delete()
            connections.discard(conn.connection_name)

        await cls._reset_apps()

    @classmethod
    def _init_timezone(cls, use_tz: bool, timezone: str) -> None:
        os.environ["USE_TZ"] = str(use_tz)
        os.environ["TIMEZONE"] = timezone
        _reset_timezone_cache()


def run_async(coro: Coroutine) -> None:
    """
    Simple async runner that cleans up DB connections on exit.
    This is meant for simple scripts.

    Usage::

        from tortoise import Tortoise, run_async

        async def do_stuff():
            await Tortoise.init(
                db_url='sqlite://db.sqlite3',
                models={'models': ['app.models']}
            )

            ...

        run_async(do_stuff())
    """

    async def main() -> None:
        try:
            await coro
        finally:
            await connections.close_all(discard=True)

    with from_thread.start_blocking_portal() as portal:
        portal.call(main)


__version__ = "0.25.3"


__all__ = [
    "BackwardFKRelation",
    "BackwardOneToOneRelation",
    "Model",
    "ForeignKeyFieldInstance",
    "ManyToManyFieldInstance",
    "OneToOneFieldInstance",
    "Tortoise",
    "BaseDBAsyncClient",
    "TortoiseConfig",
    "__version__",
    "connections",
]
