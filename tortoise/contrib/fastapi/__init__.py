from __future__ import annotations

import sys
import warnings
from collections.abc import Generator, Iterable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from types import ModuleType
from typing import TYPE_CHECKING

from tortoise import Tortoise, connections
from tortoise.exceptions import DoesNotExist, IntegrityError
from tortoise.log import logger

if TYPE_CHECKING:
    from fastapi import FastAPI, Request


if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


def tortoise_exception_handlers() -> dict:
    from fastapi.responses import JSONResponse

    async def doesnotexist_exception_handler(request: "Request", exc: DoesNotExist):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    async def integrityerror_exception_handler(request: "Request", exc: IntegrityError):
        return JSONResponse(
            status_code=422,
            content={"detail": [{"loc": [], "msg": str(exc), "type": "IntegrityError"}]},
        )

    return {
        DoesNotExist: doesnotexist_exception_handler,
        IntegrityError: integrityerror_exception_handler,
    }


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
        app: FastAPI | None = None,
        config: dict | None = None,
        config_file: str | None = None,
        db_url: str | None = None,
        modules: dict[str, Iterable[str | ModuleType]] | None = None,
        generate_schemas: bool = False,
        add_exception_handlers: bool = False,
        use_tz: bool = False,
        timezone: str = "UTC",
        _create_db: bool = False,
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

        if add_exception_handlers and app is not None:
            from starlette.middleware.exceptions import ExceptionMiddleware

            warnings.warn(
                "Setting `add_exception_handlers` to be true is deprecated, "
                "use `FastAPI(exception_handlers=tortoise_exception_handlers())` instead."
                "See more about it on https://tortoise.github.io/examples/fastapi",
                DeprecationWarning,
            )
            original_call_func = ExceptionMiddleware.__call__

            async def wrap_middleware_call(self, *args, **kw) -> None:
                if DoesNotExist not in self._exception_handlers:
                    self._exception_handlers.update(tortoise_exception_handlers())
                await original_call_func(self, *args, **kw)

            ExceptionMiddleware.__call__ = wrap_middleware_call  # type:ignore

    async def init_orm(self) -> None:  # pylint: disable=W0612
        await Tortoise.init(
            config=self.config,
            config_file=self.config_file,
            db_url=self.db_url,
            modules=self.modules,
            use_tz=self.use_tz,
            timezone=self.timezone,
            _create_db=self._create_db,
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
            return await self.__aenter__()

        return _self().__await__()


def register_tortoise(
    app: "FastAPI",
    config: dict | None = None,
    config_file: str | None = None,
    db_url: str | None = None,
    modules: dict[str, Iterable[str | ModuleType]] | None = None,
    generate_schemas: bool = False,
    add_exception_handlers: bool = False,
) -> None:
    """
    Registers Tortoise-ORM with set-up at the beginning of FastAPI application's lifespan
    (which allow user to read/write data from/to db inside the lifespan function),
    and tear-down at the end of that lifespan.

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
    from fastapi.routing import _merge_lifespan_context

    # Leave this function here to compare with old versions
    # So people can upgrade tortoise-orm in running project without changing any code

    @asynccontextmanager
    async def orm_lifespan(app_instance: "FastAPI"):
        async with RegisterTortoise(
            app_instance,
            config,
            config_file,
            db_url,
            modules,
            generate_schemas,
        ):
            yield

    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = _merge_lifespan_context(orm_lifespan, original_lifespan)

    if add_exception_handlers:
        for exp_type, endpoint in tortoise_exception_handlers().items():
            app.exception_handler(exp_type)(endpoint)
