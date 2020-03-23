from enum import Enum

Signals = Enum("Signals", ["pre_save", "post_save", "pre_delete", "post_delete"])


def post_save(*senders):
    def decorator(f):
        for sender in senders:
            sender.register_listener(Signals.post_save, f)
        return f

    return decorator


def pre_save(*senders):
    def decorator(f):
        for sender in senders:
            sender.register_listener(Signals.pre_save, f)
        return f

    return decorator


def pre_delete(*senders):
    def decorator(f):
        for sender in senders:
            sender.register_listener(Signals.pre_delete, f)
        return f

    return decorator


def post_delete(*senders):
    def decorator(f):
        for sender in senders:
            sender.register_listener(Signals.post_delete, f)
        return f

    return decorator
