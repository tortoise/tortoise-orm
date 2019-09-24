import logging
from typing import List

logger = logging.getLogger("tortoise")


def get_schema_sql(client, safe: bool) -> str:
    generator = client.schema_generator(client)
    return generator.get_create_schema_sql(safe)


async def generate_schema_for_client(client, safe: bool) -> None:
    generator = client.schema_generator(client)
    schema = get_schema_sql(client, safe)
    logger.debug("Creating schema: %s", schema)
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
