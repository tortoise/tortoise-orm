from enum import Enum
from typing import Callable, TypeVar

T = TypeVar("T")
FuncType = Callable[[T], T]
Signals = Enum("Signals", ["pre_save", "post_save", "pre_delete", "post_delete"])


def post_save(*senders) -> FuncType:
    """
    Register given models post_save signal.

    :param senders: Model class
    """

    def decorator(f: T) -> T:
        for sender in senders:
            sender.register_listener(Signals.post_save, f)
        return f

    return decorator


def pre_save(*senders) -> FuncType:
    """
    Register given models pre_save signal.

    :param senders: Model class
    """

    def decorator(f: T) -> T:
        for sender in senders:
            sender.register_listener(Signals.pre_save, f)
        return f

    return decorator


def pre_delete(*senders) -> FuncType:
    """
    Register given models pre_delete signal.

    :param senders: Model class
    """

    def decorator(f: T) -> T:
        for sender in senders:
            sender.register_listener(Signals.pre_delete, f)
        return f

    return decorator


def post_delete(*senders) -> FuncType:
    """
    Register given models post_delete signal.

    :param senders: Model class
    """

    def decorator(f: T) -> T:
        for sender in senders:
            sender.register_listener(Signals.post_delete, f)
        return f

    return decorator
