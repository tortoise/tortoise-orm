from __future__ import annotations

from collections.abc import AsyncIterator, Iterable, Mapping
from contextlib import asynccontextmanager
from types import ModuleType
from typing import Any, cast

import starlette
from starlette.applications import Starlette  # pylint: disable=E0401
from starlette.types import ASGIApp, Lifespan, Receive, Scope, Send

from tortoise import Tortoise
from tortoise.config import TortoiseConfig
from tortoise.connection import get_connections
from tortoise.context import TortoiseContext, get_current_context
from tortoise.log import logger

_TORTOISE_CONTEXT_STATE = "_tortoise_context"


class TortoiseContextMiddleware:
    def __init__(self, app: ASGIApp, config: TortoiseConfig, starlette_app: Starlette) -> None:
        self.app = app
        self.config = config
        self.starlette_app = starlette_app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return

        app_context = getattr(self.starlette_app.state, _TORTOISE_CONTEXT_STATE, None)
        if app_context is None:
            async with TortoiseContext() as request_context:
                await request_context.init(self.config)
                await self.app(scope, receive, send)
            return

        if get_current_context() is not app_context:
            with app_context:
                await self.app(scope, receive, send)
            return

        await self.app(scope, receive, send)


def _is_custom_lifespan(original_lifespan: Any) -> bool:
    try:
        from starlette.routing import _DefaultLifespan
    except ImportError:
        return True
    else:
        return not isinstance(original_lifespan, _DefaultLifespan)


def register_tortoise(
    app: Starlette,
    config: dict[str, Any] | TortoiseConfig | None = None,
    config_file: str | None = None,
    db_url: str | None = None,
    modules: dict[str, Iterable[str | ModuleType]] | None = None,
    generate_schemas: bool = False,
) -> None:
    """
    Registers ``startup`` and ``shutdown`` events to set-up and tear-down Tortoise-ORM
    inside a Starlette application.

    You can configure using only one of ``config``, ``config_file``
    and ``(db_url, modules)``.

    Parameters
    ----------
    app:
        Starlette app.
    config:
        Dict containing config:

        Example
        -------

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
                    'default': 'postgres://postgres:qwerty123@localhost:5432/events'
                },
                'apps': {
                    'models': {
                        'models': ['__main__'],
                        # If no default_connection specified, defaults to 'default'
                        'default_connection': 'default',
                    }
                }
            }

    config_file:
        Path to .json or .yml (if PyYAML installed) file containing config with
        same format as above.
    db_url:
        Use a DB_URL string. See :ref:`db_url`
    modules:
        Dictionary of ``key``: [``list_of_modules``] that defined "apps" and modules that
        should be discovered for models.
    generate_schemas:
        True to generate schema immediately. Only useful for dev environments
        or SQLite ``:memory:`` databases

    Raises
    ------
    ConfigurationError
        For any configuration error
    """
    typed_config = TortoiseConfig.resolve_args(config, config_file, db_url, modules)

    async def init_orm() -> None:  # pylint: disable=W0612
        ctx = await Tortoise.init(config=typed_config, _enable_global_fallback=True)
        setattr(app.state, _TORTOISE_CONTEXT_STATE, ctx)
        logger.info("Tortoise-ORM started, %s, %s", get_connections()._get_storage(), Tortoise.apps)
        if generate_schemas:
            logger.info("Tortoise-ORM generating schema")
            await Tortoise.generate_schemas()

    async def close_orm() -> None:  # pylint: disable=W0612
        await Tortoise.close_connections()
        if hasattr(app.state, _TORTOISE_CONTEXT_STATE):
            delattr(app.state, _TORTOISE_CONTEXT_STATE)
        logger.info("Tortoise-ORM shutdown")

    if starlette.__version__ < "1":
        if (on_event := getattr(app, "on_event", None)) is not None:
            on_event("startup")(init_orm)
            on_event("shutdown")(close_orm)
        return

    original_lifespan = app.router.lifespan_context

    if generate_schemas or _is_custom_lifespan(original_lifespan):

        @asynccontextmanager
        async def orm_inited_lifespan(app_: Starlette) -> AsyncIterator[Mapping[str, Any] | None]:
            await init_orm()
            try:
                async with original_lifespan(app_) as maybe_state:
                    yield maybe_state
            finally:
                await close_orm()

        app.router.lifespan_context = cast("Lifespan[Any]", orm_inited_lifespan)

    if not any(
        middleware.cls is TortoiseContextMiddleware  # type:ignore[comparison-overlap]
        for middleware in app.user_middleware
    ):
        app.add_middleware(TortoiseContextMiddleware, config=typed_config, starlette_app=app)
