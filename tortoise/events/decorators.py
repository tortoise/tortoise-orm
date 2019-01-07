from typing import Callable, List, Type

from tortoise.events.events import EventList
from tortoise.events import Emitter


def handles_event(emitter: Emitter, event: Callable):
    def decorator(handler: Callable):
        emitter.subscribe(event, handler)
        return handler

    return decorator


def emits(*possible_events: List[Type[EventList]]):
    """A simple decorator that """

    def class_decorator(cls: Type):

        if hasattr(cls, "_emit"):
            cls.emit.add_events(*possible_events)
        else:
            cls.emit = Emitter(*possible_events)

        return cls

    return class_decorator
