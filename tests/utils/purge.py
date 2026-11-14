import sys


def purge_app_modules(*app_names: str) -> None:
    """Drop cached modules for the given app labels.

    Tests write app packages under fresh ``tmp_path`` directories but reuse the
    same label, so ``sys.modules`` would otherwise serve stale code from a
    previous test.
    """
    for name in list(sys.modules):
        if any(name == app or name.startswith(f"{app}.") for app in app_names):
            del sys.modules[name]
