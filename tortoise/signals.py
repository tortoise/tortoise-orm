from enum import Enum
from typing import Callable, Type

from tortoise import Model

Signals = Enum("Signals", ["pre_save", "post_save", "pre_delete", "post_delete"])


def post_save(*senders: Type[Model]) -> Callable:
    def decorator(f):
        for sender in senders:
            sender.register_listener(Signals.post_save, f)
        return f

    return decorator


def pre_save(*senders: Type[Model]) -> Callable:
    def decorator(f):
        for sender in senders:
            sender.register_listener(Signals.pre_save, f)
        return f

    return decorator


def pre_delete(*senders: Type[Model]) -> Callable:
    def decorator(f):
        for sender in senders:
            sender.register_listener(Signals.pre_delete, f)
        return f

    return decorator


def post_delete(*senders: Type[Model]) -> Callable:
    def decorator(f):
        for sender in senders:
            sender.register_listener(Signals.post_delete, f)
        return f

    return decorator
