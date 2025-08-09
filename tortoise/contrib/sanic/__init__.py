from __future__ import annotations

from collections.abc import Callable, Iterable
from types import ModuleType
from typing import Dict, Optional, Union

from sanic import Sanic, Request, HTTPResponse  # pylint: disable=E0401
from sanic.response import json

from tortoise import Tortoise, connections
from tortoise.exceptions import DoesNotExist, IntegrityError
from tortoise.log import logger


def tortoise_exception_handlers() -> Dict[type[Exception], Callable]:
    """Create exception handlers for Tortoise ORM exceptions.
    
    Returns:
        Dictionary mapping exception types to handler functions
    """
    async def doesnotexist_exception_handler(request: Request, exc: DoesNotExist) -> HTTPResponse:
        return json({"detail": str(exc)}, status=404)
    
    async def integrityerror_exception_handler(request: Request, exc: IntegrityError) -> HTTPResponse:
        return json(
            {"detail": [{"loc": [], "msg": str(exc), "type": "IntegrityError"}]}, 
            status=422
        )
    
    return {
        DoesNotExist: doesnotexist_exception_handler,
        IntegrityError: integrityerror_exception_handler,
    }


def register_tortoise(
    app: Sanic,
    config: Optional[Dict] = None,
    config_file: Optional[str] = None,
    db_url: Optional[str] = None,
    modules: Optional[Dict[str, Iterable[Union[str, ModuleType]]]] = None,
    generate_schemas: bool = False,
    add_exception_handlers: bool = False,
    use_tz: bool = False,
    timezone: str = "UTC",
    _create_db: bool = False,
) -> None:
    """
    Registers ``before_server_start`` and ``after_server_stop`` hooks to set-up and tear-down
    Tortoise-ORM inside a Sanic webserver.

    You can configure using only one of ``config``, ``config_file``
    and ``(db_url, modules)``.

    Parameters
    ----------
    app:
        Sanic app.
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
    _create_db:
        If True, tries to create database automatically.

    Raises
    ------
    ConfigurationError
        For any configuration error
    """

    async def tortoise_init() -> None:
        await Tortoise.init(
            config=config, 
            config_file=config_file, 
            db_url=db_url, 
            modules=modules,
            use_tz=use_tz,
            timezone=timezone,
            _create_db=_create_db,
        )
        logger.info("Tortoise-ORM started, %s, %s", connections._get_storage(), Tortoise.apps)  # pylint: disable=W0212

    if generate_schemas:

        @app.main_process_start
        async def init_orm_main(app):  # pylint: disable=W0612
            await tortoise_init()
            logger.info("Tortoise-ORM generating schema")
            await Tortoise.generate_schemas()

    @app.before_server_start
    async def init_orm(app):
        await tortoise_init()
        if generate_schemas and getattr(app, "_test_manager", None):
            # Running by sanic-testing
            await Tortoise.generate_schemas()

    @app.after_server_stop
    async def close_orm(app):  # pylint: disable=W0612
        await connections.close_all()
        logger.info("Tortoise-ORM shutdown")
    
    if add_exception_handlers:
        for exc_type, handler in tortoise_exception_handlers().items():
            app.error_handler.add(exc_type, handler)
