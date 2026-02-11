class TortoiseLoopSwitchWarning(UserWarning):
    """Emitted when a Tortoise connection detects an event loop change.

    This typically means the connection pool was created on one event loop,
    but is now being used on a different one. Tortoise will transparently
    create a fresh connection for the new loop.

    In **test environments**, this is expected (e.g., function-scoped fixtures,
    Starlette TestClient). Use ``tortoise_test_context()`` to suppress this
    warning automatically, or suppress it manually::

        import warnings
        from tortoise.warnings import TortoiseLoopSwitchWarning
        warnings.filterwarnings("ignore", category=TortoiseLoopSwitchWarning)

    In **production**, this warning usually indicates a bug -- investigate why
    the event loop changed between connection creation and use.
    """
