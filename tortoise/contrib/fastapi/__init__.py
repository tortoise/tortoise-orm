from __future__ import annotations

import sys
import warnings
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from types import ModuleType
from typing import TYPE_CHECKING, Dict, Generator, Iterable, Optional, Union

from fastapi.responses import JSONResponse
from pydantic import BaseModel  # pylint: disable=E0611
from starlette.routing import _DefaultLifespan

from tortoise import Tortoise, connections
from tortoise.exceptions import DoesNotExist, IntegrityError
from tortoise.log import logger

if TYPE_CHECKING:
    from fastapi import FastAPI, Request

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


class HTTPNotFoundError(BaseModel):
    detail: str


class RegisterTortoise(AbstractAsyncContextManager):
    """
    Registers Tortoise-ORM with set-up and tear-down
    inside a FastAPI application's lifespan.

    You can configure using only one of ``config``, ``config_file``
    and ``(db_url, modules)``.

    Parameters
    ----------
    app:
        FastAPI app.
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
    add_exception_handlers:
        True to add some automatic exception handlers for ``DoesNotExist`` & ``IntegrityError``.
        This is not recommended for production systems as it may leak data.
    use_tz:
        A boolean that specifies if datetime will be timezone-aware by default or not.
    timezone:
        Timezone to use, default is UTC.

    Raises
    ------
    ConfigurationError
        For any configuration error
    """

    def __init__(
        self,
        app: FastAPI,
        config: Optional[dict] = None,
        config_file: Optional[str] = None,
        db_url: Optional[str] = None,
        modules: Optional[Dict[str, Iterable[Union[str, ModuleType]]]] = None,
        generate_schemas: bool = False,
        add_exception_handlers: bool = False,
        use_tz: bool = False,
        timezone: str = "UTC",
    ) -> None:
        self.app = app
        self.config = config
        self.config_file = config_file
        self.db_url = db_url
        self.modules = modules
        self.generate_schemas = generate_schemas
        self.use_tz = use_tz
        self.timezone = timezone

        if add_exception_handlers:

            @app.exception_handler(DoesNotExist)
            async def doesnotexist_exception_handler(request: "Request", exc: DoesNotExist):
                return JSONResponse(status_code=404, content={"detail": str(exc)})

            @app.exception_handler(IntegrityError)
            async def integrityerror_exception_handler(request: "Request", exc: IntegrityError):
                return JSONResponse(
                    status_code=422,
                    content={"detail": [{"loc": [], "msg": str(exc), "type": "IntegrityError"}]},
                )

    async def init_orm(self) -> None:  # pylint: disable=W0612
        await Tortoise.init(
            config=self.config,
            config_file=self.config_file,
            db_url=self.db_url,
            modules=self.modules,
            use_tz=self.use_tz,
            timezone=self.timezone,
        )
        logger.info("Tortoise-ORM started, %s, %s", connections._get_storage(), Tortoise.apps)
        if self.generate_schemas:
            logger.info("Tortoise-ORM generating schema")
            await Tortoise.generate_schemas()

    @staticmethod
    async def close_orm() -> None:  # pylint: disable=W0612
        await connections.close_all()
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
            await self.init_orm()
            return self

        return _self().__await__()


def register_tortoise(
    app: "FastAPI",
    config: Optional[dict] = None,
    config_file: Optional[str] = None,
    db_url: Optional[str] = None,
    modules: Optional[Dict[str, Iterable[Union[str, ModuleType]]]] = None,
    generate_schemas: bool = False,
    add_exception_handlers: bool = False,
) -> None:
    """
    Registers ``startup`` and ``shutdown`` events to set-up and tear-down Tortoise-ORM
    inside a FastAPI application.

    You can configure using only one of ``config``, ``config_file``
    and ``(db_url, modules)``.

    Parameters
    ----------
    app:
        FastAPI app.
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
    add_exception_handlers:
        True to add some automatic exception handlers for ``DoesNotExist`` & ``IntegrityError``.
        This is not recommended for production systems as it may leak data.

    Raises
    ------
    ConfigurationError
        For any configuration error
    """
    orm = RegisterTortoise(
        app,
        config,
        config_file,
        db_url,
        modules,
        generate_schemas,
        add_exception_handlers,
    )
    if isinstance(lifespan := app.router.lifespan_context, _DefaultLifespan):
        # Leave on_event here to compare with old versions
        # So people can upgrade tortoise-orm in running project without changing any code

        @app.on_event("startup")  # type: ignore[unreachable]
        async def init_orm() -> None:  # pylint: disable=W0612
            await orm.init_orm()

        @app.on_event("shutdown")
        async def close_orm() -> None:  # pylint: disable=W0612
            await orm.close_orm()

    else:
        # If custom lifespan was passed to app, register tortoise in it
        warnings.warn(
            "`register_tortoise` function is deprecated, "
            "use the `RegisterTortoise` class instead."
            "See more about it on https://tortoise.github.io/examples/fastapi",
            DeprecationWarning,
        )

        @asynccontextmanager
        async def orm_lifespan(app_instance: "FastAPI"):
            async with orm:
                async with lifespan(app_instance):
                    yield

        app.router.lifespan_context = orm_lifespan
