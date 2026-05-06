"""
Context-based state management for Tortoise ORM.

This module provides the TortoiseContext class which encapsulates all Tortoise ORM state
(connections, apps, init status, timezone, routers) into a single context object. This enables:

- Parallel test execution (each worker gets its own context)
- Event loop isolation (connections bound to context's loop)
- Clean teardown (context owns all resources)

Usage:
    async with TortoiseContext() as ctx:
        await ctx.init(db_url="sqlite://:memory:", modules={"models": ["myapp.models"]})
        await ctx.generate_schemas()
        # Models automatically use ctx.connections when context is active
        user = await User.create(name="test")
"""

from __future__ import annotations

import contextvars
import importlib
import os
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from tortoise.backends.base.config_generator import generate_config
from tortoise.config import TortoiseConfig
from tortoise.connection import ConnectionHandler
from tortoise.exceptions import ConfigurationError
from tortoise.timezone import _reset_timezone_cache

if TYPE_CHECKING:
    from collections.abc import Iterable
    from types import ModuleType

    from tortoise.apps import Apps
    from tortoise.backends.base.client import BaseDBAsyncClient
    from tortoise.models import Model


# ContextVar for tracking the current active context
_current_context: contextvars.ContextVar[TortoiseContext | None] = contextvars.ContextVar(
    "tortoise_context", default=None
)

# Optional global fallback context for cross-task access.
# This is used by RegisterTortoise (FastAPI) where asgi-lifespan runs lifespan
# in a background task, but requests/tests run in a different task.
# Disabled by default; enabled via Tortoise.init(_enable_global_fallback=True).
_global_context: TortoiseContext | None = None


def get_current_context() -> TortoiseContext | None:
    """
    Get the currently active TortoiseContext, or None if no context is active.

    Checks the contextvar first (for proper isolation), then falls back to
    the global context if one was set via _enable_global_fallback.

    Returns:
        The current TortoiseContext if one is active, None otherwise.
    """
    ctx = _current_context.get()
    if ctx is not None:
        return ctx
    return _global_context


def set_global_context(ctx: TortoiseContext) -> None:
    """
    Set the global fallback context for cross-task access.

    This is used by RegisterTortoise (FastAPI) where asgi-lifespan runs lifespan
    in a background task, but requests/tests run in a different task.
    The global context allows these cross-task scenarios to work without
    explicit context passing.

    Args:
        ctx: The TortoiseContext to set as global fallback.

    Raises:
        ConfigurationError: If a global context is already set. Only one global
            context can be active at a time. For multiple isolated contexts,
            use explicit TortoiseContext() without global fallback.
    """
    global _global_context
    if _global_context is not None:
        raise ConfigurationError(
            "Global context fallback is already enabled by another Tortoise.init() call. "
            "Only one global context can be active at a time. "
            "Use explicit TortoiseContext() for multiple isolated contexts, "
            "or set _enable_global_fallback=False for secondary apps."
        )
    _global_context = ctx


def require_context() -> TortoiseContext:
    """
    Get the currently active TortoiseContext, raising if none is active.

    Returns:
        The current TortoiseContext.

    Raises:
        RuntimeError: If no TortoiseContext is currently active.
    """
    ctx = get_current_context()
    if ctx is None:
        raise RuntimeError(
            "No TortoiseContext is currently active. "
            "Use 'async with TortoiseContext() as ctx:' to create one, "
            "or call Tortoise.init() for global state."
        )
    return ctx


class TortoiseContext:
    """
    Encapsulates all Tortoise ORM state for a single execution context.

    Each TortoiseContext instance owns:
    - A ConnectionHandler with database connections
    - An Apps registry with model definitions
    - Initialization state tracking

    Use cases:
    - Isolated test environments (pytest fixtures)
    - Parallel test execution with pytest-xdist
    - Multiple database configurations in the same process
    - Scoped database sessions with automatic cleanup

    The context is tracked via contextvars, allowing async code to
    automatically resolve the correct connections without explicit passing.

    Example:
        async with TortoiseContext() as ctx:
            await ctx.init(
                db_url="sqlite://:memory:",
                modules={"models": ["myapp.models"]}
            )
            await ctx.generate_schemas()
            # Models use this context's connections automatically
            user = await User.create(name="test")
    """

    def __init__(self) -> None:
        self._connections: ConnectionHandler | None = None
        self._apps: Apps | None = None
        self._inited: bool = False
        self._token: contextvars.Token[TortoiseContext | None] | None = None
        self._table_name_generator: Callable[[type[Model]], str] | None = None
        self._default_connection: str | None = None
        # Timezone settings
        self._use_tz: bool = True
        self._timezone: str = "UTC"
        # Routers
        self._routers: list[type] = []

    @property
    def connections(self) -> ConnectionHandler:
        """
        Get the ConnectionHandler for this context.

        Creates a new ConnectionHandler on first access (lazy initialization).
        The handler uses instance-level storage for true isolation between contexts.

        Returns:
            The ConnectionHandler instance owned by this context.
        """
        if self._connections is None:
            # ConnectionHandler always uses instance storage for isolation
            self._connections = ConnectionHandler()
        return self._connections

    @property
    def apps(self) -> Apps | None:
        """
        Get the Apps registry for this context.

        Returns:
            The Apps instance if initialized, None otherwise.
        """
        return self._apps

    @property
    def inited(self) -> bool:
        """
        Check if this context has been initialized.

        Returns:
            True if init() has been called successfully, False otherwise.
        """
        return self._inited

    @property
    def default_connection(self) -> str | None:
        """
        Get the default connection name for this context.

        Returns:
            The default connection name if one is configured, None otherwise.
            A default is automatically set when there's only one connection
            or when a connection is named "default".
        """
        return self._default_connection

    @property
    def use_tz(self) -> bool:
        """
        Check if timezone-aware datetimes are enabled.

        Returns:
            True if datetime fields are timezone-aware, False otherwise.
        """
        return self._use_tz

    @property
    def timezone(self) -> str:
        """
        Get the timezone configured for this context.

        Returns:
            The timezone string (e.g., "UTC", "America/New_York").
        """
        return self._timezone

    @property
    def routers(self) -> list[type]:
        """
        Get the database routers for this context.

        Returns:
            List of router classes configured for this context.
        """
        return self._routers

    async def init(
        self,
        config: dict[str, Any] | TortoiseConfig | None = None,
        *,
        config_file: str | None = None,
        db_url: str | None = None,
        modules: dict[str, Iterable[str | ModuleType]] | None = None,
        _create_db: bool = False,
        use_tz: bool = True,
        timezone: str = "UTC",
        routers: list[str | type] | None = None,
        table_name_generator: Callable[[type[Model]], str] | None = None,
        init_connections: bool = True,
        _enable_global_fallback: bool = False,
    ) -> None:
        """
        Initialize this context with database configuration.

        You can configure using one of: ``config``, ``config_file``, or ``(db_url, modules)``.

        This method is self-sufficient and can be used directly in tests without
        going through Tortoise.init():

            async with TortoiseContext() as ctx:
                await ctx.init(db_url="sqlite://:memory:", modules={"models": ["myapp.models"]})
                # Run tests...

        Args:
            config: Full configuration dict or TortoiseConfig with 'connections' and 'apps' keys.
            config_file: Path to .json or .yml file containing configuration.
            db_url: Database URL string (e.g., "sqlite://:memory:").
            modules: Dictionary mapping app labels to lists of model modules.
            _create_db: If True, creates the database if it doesn't exist.
            use_tz: If True, datetime fields will be timezone-aware.
            timezone: Timezone to use, defaults to "UTC".
            routers: List of database router paths or classes.
            table_name_generator: Optional callable to generate table names.
            init_connections: If False, skips initializing connection clients while still
                loading apps and validating connection names against the config.
            _enable_global_fallback: If True, sets this context as the global fallback
                for cross-task access (e.g., asgi-lifespan scenarios). Default is False.

        Raises:
            ConfigurationError: If configuration is invalid or incomplete.
        """
        from tortoise.apps import Apps

        typed_config = TortoiseConfig.resolve_args(config, config_file, db_url, modules)
        config_dict = typed_config.to_dict()
        connections_config = config_dict["connections"]
        apps_config = config_dict["apps"]

        effective_use_tz = typed_config.use_tz if typed_config.use_tz is not None else use_tz
        effective_timezone = (
            typed_config.timezone if typed_config.timezone is not None else timezone
        )
        effective_routers = typed_config.routers if typed_config.routers is not None else routers

        self._table_name_generator = table_name_generator

        if not init_connections and _create_db:
            raise ConfigurationError("init_connections=False cannot be used with _create_db=True")

        self._init_timezone(effective_use_tz, effective_timezone)

        if init_connections:
            await self.connections._init(connections_config, _create_db)
        else:
            self.connections._init_config(connections_config)

        self._apps = Apps(
            apps_config,
            self.connections,
            self._table_name_generator,
            validate_connections=init_connections,
        )

        self._init_routers(effective_routers)

        connection_names = list(typed_config.connections.keys())
        if len(connection_names) == 1:
            self._default_connection = connection_names[0]
        elif "default" in connection_names:
            self._default_connection = "default"
        else:
            self._default_connection = None

        self._inited = True

        if _enable_global_fallback:
            set_global_context(self)

    def _init_timezone(self, use_tz: bool, timezone: str) -> None:
        """Initialize timezone settings for this context."""
        self._use_tz = use_tz
        self._timezone = timezone
        # Set environment variables for backward compatibility
        os.environ["USE_TZ"] = str(use_tz)
        os.environ["TIMEZONE"] = timezone
        _reset_timezone_cache()

    def _init_routers(self, routers: list[str | type] | None = None) -> None:
        """Initialize database routers for this context."""
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
        self._routers = router_cls
        router.init_routers(router_cls)

    async def generate_schemas(self, safe: bool = True) -> None:
        """
        Generate database schemas for all models in this context.

        Args:
            safe: When True, creates tables only if they don't already exist.

        Raises:
            ConfigurationError: If context has not been initialized.
        """
        from tortoise.utils import generate_schema_for_client

        if not self._inited:
            raise ConfigurationError(
                "Context not initialized. Call init() before generating schemas."
            )
        for connection in self.connections.all():
            await generate_schema_for_client(connection, safe)

    def get_model(self, app_label: str, model_name: str) -> type[Model]:
        """
        Retrieve a model by app label and model name.

        Args:
            app_label: The app label (e.g., "models").
            model_name: The model class name (e.g., "User").

        Returns:
            The model class.

        Raises:
            ConfigurationError: If context not initialized or model not found.
        """
        if self._apps is None:
            raise ConfigurationError(
                "Context not initialized. Call init() before accessing models."
            )
        return self._apps.get_model(app_label, model_name)

    def db(self, connection_name: str | None = None) -> BaseDBAsyncClient:
        """
        Get a database connection by name.

        Args:
            connection_name: The connection alias. If None, uses the default connection.
                            With a single connection, it becomes the default automatically.
                            With multiple connections, either specify explicitly or
                            configure one as "default".

        Returns:
            The database client for the specified connection.

        Raises:
            ConfigurationError: If context not initialized, connection not found,
                               or no default connection when multiple exist.
        """
        if not self._inited:
            raise ConfigurationError(
                "Context not initialized. Call init() before accessing database."
            )

        if connection_name is None:
            if self._default_connection is None:
                raise ConfigurationError(
                    "No default connection configured. Either use a single connection, "
                    "name one 'default', or specify connection_name explicitly."
                )
            connection_name = self._default_connection

        return self.connections.get(connection_name)

    async def close_connections(self) -> None:
        """
        Close all database connections owned by this context.

        This is called automatically when exiting the async context manager.
        Also clears the global fallback if this context was set as global.
        """
        global _global_context
        if self._connections is not None:
            # Only close if connections were actually initialized
            if self._connections._db_config is not None:
                await self._connections.close_all(discard=True)
            self._connections = None
        # Clear global context if this context was set as the global fallback
        if _global_context is self:
            _global_context = None

    def __enter__(self) -> TortoiseContext:
        """
        Enter the context manager and set this context as current.

        Returns:
            This context instance.
        """
        self._token = _current_context.set(self)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Exit the context manager and restore the previous context.
        """
        if self._token is not None:
            _current_context.reset(self._token)
            self._token = None

    async def __aenter__(self) -> TortoiseContext:
        """
        Enter the async context manager and set this context as current.

        Returns:
            This context instance.
        """
        self.__enter__()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Exit the async context manager, close connections, and restore previous context.
        """
        await self.close_connections()
        self._apps = None
        self._inited = False
        self.__exit__(exc_type, exc_val, exc_tb)


@asynccontextmanager
async def tortoise_test_context(
    modules: list[str],
    db_url: str = "sqlite://:memory:",
    app_label: str = "models",
    *,
    connection_label: str | None = None,
    use_tz: bool = True,
    timezone: str = "UTC",
    routers: list[str | type] | None = None,
) -> AsyncIterator[TortoiseContext]:
    """
    Async context manager for isolated test database setup.

    This is the recommended way to set up Tortoise ORM for testing with pytest.
    Each call creates a completely isolated context with its own:
    - ConnectionHandler (no global state pollution)
    - Apps registry
    - Database (created fresh, cleaned up on exit)
    - Timezone and router configuration

    Example with pytest-asyncio:
        @pytest_asyncio.fixture
        async def db():
            async with tortoise_test_context(["myapp.models"]) as ctx:
                yield ctx

        @pytest.mark.asyncio
        async def test_create_user(db):
            user = await User.create(name="Alice")
            assert user.id is not None

    Features:
    - Creates isolated TortoiseContext (no global state pollution)
    - Creates fresh database and generates schemas
    - Cleans up connections on exit
    - xdist-safe (each worker gets own context)

    Args:
        modules: List of module paths to discover models from.
        db_url: Database URL, defaults to in-memory SQLite.
        app_label: The app label for the models, defaults to "models".
        connection_label: The connection alias name. If None, defaults to "default".
        use_tz: If True, datetime fields will be timezone-aware.
        timezone: Timezone to use, defaults to "UTC".
        routers: List of database router paths or classes.

    Yields:
        An initialized TortoiseContext ready for use.
    """
    import warnings

    from tortoise.warnings import TortoiseLoopSwitchWarning

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=TortoiseLoopSwitchWarning)
        ctx = TortoiseContext()
        async with ctx:
            config = generate_config(
                db_url,
                app_modules={app_label: modules},
                connection_label=connection_label,
                testing=True,
            )
            await ctx.init(
                config=config,
                _create_db=True,
                use_tz=use_tz,
                timezone=timezone,
                routers=routers,
            )
            await ctx.generate_schemas(safe=False)
            yield ctx


__all__ = [
    "TortoiseContext",
    "get_current_context",
    "require_context",
    "set_global_context",
    "tortoise_test_context",
]
