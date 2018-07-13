class QueryAsyncIterator:
    def __init__(self, query, callback=None):
        self.query = query
        self.sequence = None
        self._sequence_iterator = None
        self._callback = callback

    def __aiter__(self):
        return self

    async def fetch_sequence(self) -> None:
        self.sequence = await self.query
        self._sequence_iterator = self.sequence.__iter__()
        if self._callback:
            await self._callback(self)

    async def __anext__(self):
        if self.sequence is None:
            await self.fetch_sequence()
        try:
            return next(self._sequence_iterator)
        except StopIteration:
            raise StopAsyncIteration


def get_schema_sql(client) -> str:
    generator = client.schema_generator(client)
    creation_string = generator.get_create_schema_sql()
    return creation_string


async def generate_schema(client) -> None:
    generator = client.schema_generator(client)
    await generator.generate_from_string(get_schema_sql(client))
