import logging
from typing import Awaitable, Callable, Iterator, List, Optional

logger = logging.getLogger("tortoise")


class QueryAsyncIterator:
    __slots__ = ("query", "sequence", "_sequence_iterator", "_callback")

    def __init__(self, query: Awaitable[Iterator], callback: Optional[Callable] = None) -> None:
        self.query = query
        self.sequence = None  # type: Optional[Iterator]
        self._sequence_iterator = None
        self._callback = callback

    def __aiter__(self):
        return self  # pragma: nocoverage

    async def __anext__(self):
        if self.sequence is None:
            self.sequence = await self.query
            self._sequence_iterator = self.sequence.__iter__()
            if self._callback:  # pragma: no branch
                await self._callback(self)
        try:
            return next(self._sequence_iterator)
        except StopIteration:
            raise StopAsyncIteration


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
