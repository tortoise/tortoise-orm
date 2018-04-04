class AsyncIteratorWrapper:
    def __init__(self, sequence):
        self.sequence_iterator = sequence.__iter__()

    async def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self.sequence_iterator)
        except StopIteration:
            raise StopAsyncIteration


async def generate_schema(client):
    generator = client.schema_generator(client)
    creation_string = generator.get_create_schema_sql()
    await generator.generate_from_string(creation_string)


async def get_schema_sql(client):
    generator = client.schema_generator(client)
    creation_string = generator.get_create_schema_sql()
    return creation_string
