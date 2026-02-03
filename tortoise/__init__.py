from __future__ import annotations

import importlib
import json
import logging
import os
import warnings
from collections.abc import Callable, Coroutine, Iterable
from types import ModuleType
from typing import TYPE_CHECKING, Any

from anyio import from_thread

from tortoise.apps import Apps
from tortoise.backends.base.client import BaseDBAsyncClient
from tortoise.backends.base.config_generator import expand_db_url
from tortoise.config import TortoiseConfig
from tortoise.connection import connections, get_connection, get_connections
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

if TYPE_CHECKING:
    from tortoise.context import TortoiseContext


class classproperty:
    """
    Descriptor that acts like @property but works on classes.

    This allows `Tortoise.apps` and `Tortoise._inited` to dynamically
    resolve to the current context's state without using a metaclass.

    Note: This only supports getters, not setters. Internal code must
    work with context directly for mutations.

    WARNING: Class-level assignment (Tortoise.apps = value) will SHADOW
    this descriptor. Python's descriptor protocol only intercepts instance-level
    assignment. Use TortoiseContext directly instead.
    """

    def __init__(self, func: Callable[..., Any]) -> None:
        self.func = func

    def __get__(self, obj: Any, objtype: type | None = None) -> Any:
        return self.func(objtype)


class Tortoise:
    """
    Tortoise ORM main interface.

    Provides static methods for initialization and access to ORM state.
    All state is managed by TortoiseContext instances.

    NOTE: No class-level state except table_name_generator for backward compat.
    All runtime state lives in TortoiseContext.
    """

    # Class-level for backward compatibility; also stored in TortoiseContext
    table_name_generator: Callable[[type[Model]], str] | None = None

    @classmethod
    def _get_context(cls) -> TortoiseContext | None:
        """Get the current context from context var."""
        from tortoise.context import get_current_context

        return get_current_context()

    @classmethod
    def _require_context(cls) -> TortoiseContext:
        """Get the current context, raising if none exists."""
        ctx = cls._get_context()
        if ctx is None:
            raise ConfigurationError(
                "Tortoise ORM is not initialized. Call Tortoise.init() first "
                "or use 'async with TortoiseContext()' for explicit context management."
            )
        return ctx

    # BACKWARD COMPATIBLE: Class properties (no metaclass needed!)
    @classproperty
    def apps(cls) -> Apps | None:
        """
        Get the Apps registry from current context.

        Returns None if no context is active.
        """
        ctx = cls._get_context()
        return ctx.apps if ctx else None

    @classproperty
    def _inited(cls) -> bool:
        """
        Check if Tortoise is initialized.

        Returns False if no context is active.
        """
        ctx = cls._get_context()
        return ctx.inited if ctx else False

    @classmethod
    def is_inited(cls) -> bool:
        """Check if Tortoise is initialized."""
        ctx = cls._get_context()
        return ctx.inited if ctx else False

    @classmethod
    def get_connection(cls, connection_name: str) -> BaseDBAsyncClient:
        """
        Returns the connection by name.

        :raises ConfigurationError: If connection name does not exist.

        .. warning::
           This is deprecated and will be removed in a future release. Please use
           :meth:`get_connection<tortoise.connection.get_connection>` instead.
        """
        return get_connection(connection_name)

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
        from tortoise.context import TortoiseContext, get_current_context

        # Get or create context
        ctx = get_current_context()
        if ctx is None:
            ctx = TortoiseContext()
            ctx.__enter__()

        # Create Apps if not exists
        if ctx._apps is None:
            ctx._apps = Apps({}, ctx.connections, cls.table_name_generator)
        ctx._apps._table_name_generator = cls.table_name_generator
        return ctx._apps.init_app(label, model_paths, _init_relations=_init_relations)

    @classmethod
    def _init_apps(
        cls, apps_config: dict[str, dict[str, Any]], *, validate_connections: bool = True
    ) -> None:
        """Internal: Initialize Apps registry on current context."""
        ctx = cls._require_context()
        ctx._apps = Apps(
            apps_config,
            ctx.connections,
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
        _enable_global_fallback: bool = False,
    ) -> TortoiseContext:
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
        :param _enable_global_fallback:
            When ``True``, stores the context as a global fallback for cross-task access.
            This is used by RegisterTortoise (FastAPI) where asgi-lifespan runs lifespan
            in a background task. Default is ``False`` for pure context isolation.

        :raises ConfigurationError: For any configuration error

        :returns: The TortoiseContext that was initialized. For multiple asyncio.run()
            calls, capture this and use 'with ctx:' to maintain context.
        """
        from tortoise.context import TortoiseContext, _current_context

        # Get or create context - only use contextvar, not global fallback.
        # Global fallback is for reading (queries), not for initialization.
        # This allows multiple apps to initialize independently even if one
        # has global fallback enabled.
        ctx = _current_context.get()
        if ctx is None:
            ctx = TortoiseContext()
            ctx.__enter__()
        elif ctx.inited:
            # Re-initializing existing context
            await ctx.close_connections()

        # Validate config source - must provide exactly one
        if int(bool(config) + bool(config_file) + bool(db_url)) != 1:
            raise ConfigurationError(
                'You should init either from "config", "config_file" or "db_url"'
            )

        # Normalize config: handle config_file case
        normalized_config: dict[str, Any] | TortoiseConfig | None = config
        if config_file:
            normalized_config = cls._get_config_from_config_file(config_file)

        # Debug logging
        if logger.isEnabledFor(logging.DEBUG) and normalized_config is not None:
            if isinstance(normalized_config, TortoiseConfig):
                config_dict = normalized_config.to_dict()
            else:
                config_dict = normalized_config
            connections_config = config_dict.get("connections", {})
            apps_config = config_dict.get("apps", {})
            str_connection_config = cls.star_password(connections_config)
            logger.debug(
                "Tortoise-ORM startup\n    connections: %s\n    apps: %s",
                str_connection_config,
                str(apps_config),
            )

        # Store table_name_generator at class level for backward compatibility
        cls.table_name_generator = table_name_generator

        # Delegate to context init
        await ctx.init(
            config=normalized_config,
            db_url=db_url,
            modules=modules,
            _create_db=_create_db,
            use_tz=use_tz,
            timezone=timezone,
            routers=routers,
            table_name_generator=table_name_generator,
            init_connections=init_connections,
            _enable_global_fallback=_enable_global_fallback,
        )

        return ctx

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
        """
        await get_connections().close_all()
        logger.info("Tortoise-ORM shutdown")

    @classmethod
    async def _reset_apps(cls) -> None:
        """Internal: Reset Apps registry on current context."""
        ctx = cls._get_context()
        if ctx is None or ctx._apps is None:
            return

        for model in ctx._apps.get_models_iterable():
            if isinstance(model, ModelMeta):
                model._meta.default_connection = None
        ctx._apps.clear()
        ctx._apps = None

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
        for connection in get_connections().all():
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
        conn_handler = get_connections()
        await conn_handler.close_all(discard=False)
        for conn in conn_handler.all():
            await conn.db_delete()
            conn_handler.discard(conn.connection_name)

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
    from tortoise.context import get_current_context

    async def main() -> None:
        try:
            await coro
        finally:
            ctx = get_current_context()
            if ctx is not None:
                await ctx.connections.close_all(discard=True)

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
