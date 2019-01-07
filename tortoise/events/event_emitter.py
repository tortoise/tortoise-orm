class EventEmitter:
    """An emitter for a specific event."""

    def __init__(self, emitter, event):
        self.emitter = emitter
        self.event = event

    def __iadd__(self, handler):
        self.emitter.subscribe(self, handler)
        return self

    def __isub__(self, handler):
        self.emitter.unsubscribe(self, handler)
        return self

    def __call__(self, *args, **kwargs):
        self.emitter.emit(self, *args, **kwargs)


class AsyncEventEmitter(EventEmitter):

    async def __call__(self, *args, **kwargs):
        await self.emitter.emit(self, *args, **kwargs)
