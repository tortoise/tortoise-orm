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
