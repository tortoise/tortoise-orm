import sys
from typing import TYPE_CHECKING, Any, Iterable, Optional, Tuple

from tortoise.log import logger

if sys.version_info >= (3, 12):
    from itertools import batched
else:
    from itertools import islice

    def batched(iterable: Iterable[Any], n: int) -> Iterable[Tuple[Any]]:
        it = iter(iterable)
        while batch := tuple(islice(it, n)):
            yield batch


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
    if schema := generator.get_create_schema_sql(safe):  # pragma: nobranch
        if client.schema_generator.DIALECT == "mysql":
            # MySQL does not support 'IF NOT EXISTS' syntax for `INDEX`
            schema = schema.replace(" INDEX IF NOT EXISTS", " INDEX")
        logger.debug("Creating schema: %s", schema)
        await generator.generate_from_string(schema)


def chunk(instances: Iterable[Any], batch_size: Optional[int] = None) -> Iterable[Iterable[Any]]:
    """
    Generate iterable chunk by batch_size
    # noqa: DAR301
    """
    if not batch_size:
        yield instances
    else:
        yield from batched(instances, batch_size)
