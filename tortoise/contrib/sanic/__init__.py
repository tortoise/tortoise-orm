from __future__ import annotations

from collections.abc import Iterable
from types import ModuleType

from sanic import Sanic  # pylint: disable=E0401

from tortoise import Tortoise, connections
from tortoise.log import logger


def register_tortoise(
    app: Sanic,
    config: dict | None = None,
    config_file: str | None = None,
    db_url: str | None = None,
    modules: dict[str, Iterable[str | ModuleType]] | None = None,
    generate_schemas: bool = False,
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

    Raises
    ------
    ConfigurationError
        For any configuration error
    """

    async def tortoise_init() -> None:
        await Tortoise.init(config=config, config_file=config_file, db_url=db_url, modules=modules)
        logger.info(
            "Tortoise-ORM started, %s, %s", connections._get_storage(), Tortoise.apps
        )  # pylint: disable=W0212

    if generate_schemas:

        @app.listener("main_process_start")
        async def init_orm_main(app, loop):  # pylint: disable=W0612
            await tortoise_init()
            logger.info("Tortoise-ORM generating schema")
            await Tortoise.generate_schemas()

    @app.listener("before_server_start")
    async def init_orm(app, loop):  # pylint: disable=W0612
        await tortoise_init()

    @app.listener("after_server_stop")
    async def close_orm(app, loop):  # pylint: disable=W0612
        await connections.close_all()
        logger.info("Tortoise-ORM shutdown")
