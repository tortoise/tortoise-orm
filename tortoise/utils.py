import sys
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Optional

from tortoise.log import logger

if sys.version_info >= (3, 12):
    from itertools import batched
else:
    from itertools import islice

    def batched(iterable: Iterable[Any], n: int) -> Iterable[tuple[Any]]:
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
    schema = get_schema_sql(client, safe)
    logger.debug("Creating schema: %s", schema)
    if schema:  # pragma: nobranch
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
