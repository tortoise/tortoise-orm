from typing import TYPE_CHECKING

from tortoise.log import logger

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.backends.base.client import BaseDBAsyncClient


def get_schema_sql(client: "BaseDBAsyncClient", safe: bool) -> str:
    """
    Generates the SQL schema for the given client.

    :param client: The DB client to generate Schema SQL for
    :param safe: When set to true, creates the table only when it does not already exist.
    """
    generator = client.schema_generator(client)
    return generator.get_create_schema_sql(safe)


async def generate_schema_for_client(client: "BaseDBAsyncClient", safe: bool) -> None:
    """
    Generates and applies the SQL schema directly to the given client.

    :param client: The DB client to generate Schema SQL for
    :param safe: When set to true, creates the table only when it does not already exist.
    """
    generator = client.schema_generator(client)
    schema = get_schema_sql(client, safe)
    logger.debug("Creating schema: %s", schema)
    if schema:  # pragma: nobranch
        await generator.generate_from_string(schema)
