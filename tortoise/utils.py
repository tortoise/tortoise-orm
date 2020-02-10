import logging
from typing import TYPE_CHECKING, List

logger = logging.getLogger("tortoise")

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.backends.base.client import BaseDBAsyncClient


def get_schema_sql(client: "BaseDBAsyncClient", safe: bool) -> str:
    """
    Generates the SQL schema for the given client.

    :param client:
    :param safe:
    """
    generator = client.schema_generator(client)
    return generator.get_create_schema_sql(safe)


async def generate_schema_for_client(client: "BaseDBAsyncClient", safe: bool) -> None:
    """
    Generates and applies the SQL schema directly to the given client.

    :param client:
    :param safe:
    """
    generator = client.schema_generator(client)
    schema = get_schema_sql(client, safe)
    logger.debug("Creating schema: %s", schema)
    if schema:  # pragma: nobranch
        await generator.generate_from_string(schema)


def get_escape_translation_table() -> List[str]:
    """escape sequence taken based on definition provided by PostgreSQL and MySQL"""
    _escape_table = [chr(x) for x in range(128)]
    _escape_table[0] = "\\0"
    _escape_table[ord("\\")] = "\\\\"
    _escape_table[ord("\n")] = "\\n"
    _escape_table[ord("\r")] = "\\r"
    _escape_table[ord("\032")] = "\\Z"
    _escape_table[ord('"')] = '\\"'
    _escape_table[ord("'")] = "\\'"
    return _escape_table
