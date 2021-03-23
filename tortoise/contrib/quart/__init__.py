import asyncio
import logging
from types import ModuleType
from typing import Dict, Iterable, Optional, Union

from quart import Quart  # pylint: disable=E0401

from tortoise import Tortoise


def register_tortoise(
    app: Quart,
    config: Optional[dict] = None,
    config_file: Optional[str] = None,
    db_url: Optional[str] = None,
    modules: Optional[Dict[str, Iterable[Union[str, ModuleType]]]] = None,
    generate_schemas: bool = False,
) -> None:
    """
    Registers ``before_serving`` and ``after_serving`` hooks to set-up and tear-down Tortoise-ORM
    inside a Quart service.
    It also registers a CLI command ``generate_schemas`` that will generate the schemas.

    You can configure using only one of ``config``, ``config_file``
    and ``(db_url, modules)``.

    Parameters
    ----------
    app:
        Quart app.
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
    _generate_schemas = generate_schemas

    @app.before_serving
    async def init_orm() -> None:  # pylint: disable=W0612
        await Tortoise.init(config=config, config_file=config_file, db_url=db_url, modules=modules)
        logging.info("Tortoise-ORM started, %s, %s", Tortoise._connections, Tortoise.apps)
        if _generate_schemas:
            logging.info("Tortoise-ORM generating schema")
            await Tortoise.generate_schemas()

    @app.after_serving
    async def close_orm() -> None:  # pylint: disable=W0612
        await Tortoise.close_connections()
        logging.info("Tortoise-ORM shutdown")

    @app.cli.command()  # type: ignore
    def generate_schemas() -> None:  # pylint: disable=E0102
        """Populate DB with Tortoise-ORM schemas."""

        async def inner() -> None:
            await Tortoise.init(
                config=config, config_file=config_file, db_url=db_url, modules=modules
            )
            await Tortoise.generate_schemas()
            await Tortoise.close_connections()

        logging.basicConfig(level=logging.DEBUG)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(inner())
