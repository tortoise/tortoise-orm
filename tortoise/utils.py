from typing import Awaitable, Callable, Iterator, Optional


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
    await generator.generate_from_string(get_schema_sql(client, safe))
