from types import ModuleType
from typing import Dict, Iterable, Optional, Union

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel  # pylint: disable=E0611

from tortoise import Tortoise, connections
from tortoise.exceptions import DoesNotExist, IntegrityError
from tortoise.log import logger


class HTTPNotFoundError(BaseModel):
    detail: str


class RegisterTortoise:
    def __init__(
        self,
        app: FastAPI,
        config: Optional[dict] = None,
        config_file: Optional[str] = None,
        db_url: Optional[str] = None,
        modules: Optional[Dict[str, Iterable[Union[str, ModuleType]]]] = None,
        generate_schemas: bool = False,
        add_exception_handlers: bool = False,
    ):
        """
        Offer functions to set-up or tear-down Tortoise-ORM for the FastAPI app's lifespan.

        Usage::
            >>> @asyncontextmanager
            ... async def lifespan(app):
            ...     await RegisterTortoise(app, ...).init()
            ...     yield
            ...     await RegisterTortoise.close()
            >>> app = FastAPI(lifespan=lifespan)

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
        self.app = app
        self.config = config
        self.config_file = config_file
        self.db_url = db_url
        self.modules = modules
        self.generate_schemas = generate_schemas
        self.add_exception_handlers = add_exception_handlers

    async def init(self, init_exception_handlers=True) -> None:
        await Tortoise.init(
            config=self.config,
            config_file=self.config_file,
            db_url=self.db_url,
            modules=self.modules,
        )
        logger.info("Tortoise-ORM started, %s, %s", connections._get_storage(), Tortoise.apps)
        if self.generate_schemas:
            logger.info("Tortoise-ORM generating schema")
            await Tortoise.generate_schemas()
        if init_exception_handlers and self.add_exception_handlers:
            self.config_exception_handlers(self.app)

    @staticmethod
    async def close() -> None:
        await connections.close_all()
        logger.info("Tortoise-ORM shutdown")

    @staticmethod
    def config_exception_handlers(app) -> None:
        @app.exception_handler(DoesNotExist)
        async def doesnotexist_exception_handler(request: Request, exc: DoesNotExist):
            return JSONResponse(status_code=404, content={"detail": str(exc)})

        @app.exception_handler(IntegrityError)
        async def integrityerror_exception_handler(request: Request, exc: IntegrityError):
            return JSONResponse(
                status_code=422,
                content={"detail": [{"loc": [], "msg": str(exc), "type": "IntegrityError"}]},
            )


def register_tortoise(
    app: FastAPI,
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
    orm = RegisterTortoise(app, config, config_file, db_url, modules, generate_schemas)

    @app.on_event("startup")
    async def init_orm() -> None:  # pylint: disable=W0612
        await orm.init(False)

    @app.on_event("shutdown")
    async def close_orm() -> None:  # pylint: disable=W0612
        await orm.close()

    if add_exception_handlers:
        orm.config_exception_handlers(app)
