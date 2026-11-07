from __future__ import annotations

from collections.abc import AsyncGenerator, Generator, Iterable, Mapping
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from types import ModuleType
from typing import TYPE_CHECKING, Any, cast

from tortoise import Tortoise
from tortoise.connection import get_connections
from tortoise.log import logger

if TYPE_CHECKING:
    from starlette.applications import Starlette  # pylint: disable=E0401
    from starlette.types import Lifespan
    from typing_extensions import Self

    from tortoise.config import TortoiseConfig
    from tortoise.context import TortoiseContext


class RegisterTortoise(AbstractAsyncContextManager):
    def __init__(
        self,
        app: Starlette,
        config: dict | TortoiseConfig | None = None,
        config_file: str | None = None,
        db_url: str | None = None,
        modules: dict[str, Iterable[str | ModuleType]] | None = None,
        generate_schemas: bool = False,
        use_tz: bool = True,
        timezone: str = "UTC",
        _create_db: bool = False,
        _enable_global_fallback: bool = True,
    ) -> None:
        self.app = app
        self.config = config
        self.config_file = config_file
        self.db_url = db_url
        self.modules = modules
        self.generate_schemas = generate_schemas
        self.use_tz = use_tz
        self.timezone = timezone
        self._create_db = _create_db
        self._enable_global_fallback = _enable_global_fallback

    async def init_orm(self) -> TortoiseContext:  # pylint: disable=W0612
        ctx = await Tortoise.init(
            config=self.config,
            config_file=self.config_file,
            db_url=self.db_url,
            modules=self.modules,
            use_tz=self.use_tz,
            timezone=self.timezone,
            _create_db=self._create_db,
            _enable_global_fallback=self._enable_global_fallback,
        )
        # Store context in app.state for explicit access when global fallback is disabled
        self.app.state._tortoise_context = ctx
        logger.info("Tortoise-ORM started, %s, %s", get_connections()._get_storage(), Tortoise.apps)
        if self.generate_schemas:
            logger.info("Tortoise-ORM generating schema")
            await Tortoise.generate_schemas()
        return ctx

    async def close_orm(self) -> None:  # pylint: disable=W0612
        await Tortoise.close_connections()
        # Clear context from app.state
        if hasattr(self.app.state, "_tortoise_context"):
            delattr(self.app.state, "_tortoise_context")
        logger.info("Tortoise-ORM shutdown")

    def __call__(self, *args, **kwargs) -> Self:
        return self

    async def __aenter__(self) -> Self:
        await self.init_orm()
        return self

    async def __aexit__(self, *args, **kw) -> None:
        await self.close_orm()

    def __await__(self) -> Generator[None, None, Self]:
        async def _self() -> Self:
            return await self.__aenter__()

        return _self().__await__()


def register_tortoise(
    app: Starlette,
    config: dict | None = None,
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
    original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def orm_inited_lifespan(
        app_instance: Starlette,
    ) -> AsyncGenerator[Mapping[str, Any] | None]:
        orm = RegisterTortoise(
            app_instance,
            config,
            config_file,
            db_url,
            modules,
            generate_schemas,
        )
        async with orm, original_lifespan(app_instance) as maybe_state:
            yield maybe_state

    app.router.lifespan_context = cast("Lifespan", orm_inited_lifespan)
