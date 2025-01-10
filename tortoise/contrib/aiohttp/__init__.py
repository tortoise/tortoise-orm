from collections.abc import Iterable
from types import ModuleType
from typing import Optional, Union

from aiohttp import web  # pylint: disable=E0401

from tortoise import Tortoise, connections
from tortoise.log import logger


def register_tortoise(
    app: web.Application,
    config: Optional[dict] = None,
    config_file: Optional[str] = None,
    db_url: Optional[str] = None,
    modules: Optional[dict[str, Iterable[Union[str, ModuleType]]]] = None,
    generate_schemas: bool = False,
) -> None:
    """
    Registers ``on_startup`` and ``on_shutdown`` hooks to set-up and tear-down
    Tortoise-ORM inside a Aiohttp webserver.

    You can configure using only one of ``config``, ``config_file``
    and ``(db_url, modules)``.

    Parameters
    ----------
    app:
        Aiohttp app.
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

    async def init_orm(app):  # pylint: disable=W0612
        await Tortoise.init(config=config, config_file=config_file, db_url=db_url, modules=modules)
        logger.info(f"Tortoise-ORM started, {connections._get_storage()}, {Tortoise.apps}")
        if generate_schemas:
            logger.info("Tortoise-ORM generating schema")
            await Tortoise.generate_schemas()

    async def close_orm(app):  # pylint: disable=W0612
        await connections.close_all()
        logger.info("Tortoise-ORM shutdown")

    app.on_startup.append(init_orm)
    app.on_cleanup.append(close_orm)
