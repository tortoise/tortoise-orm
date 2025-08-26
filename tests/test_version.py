import importlib.metadata as importlib_metadata
import re
import shlex
import shutil
import subprocess  # nosec
import sys
from pathlib import Path

from tortoise import __version__

if sys.version_info >= (3, 11):
    from contextlib import chdir
else:
    import contextlib
    import os

    class chdir(contextlib.AbstractContextManager):  # Copied from source code of Python3.13
        """Non thread-safe context manager to change the current working directory."""

        def __init__(self, path) -> None:
            self.path = path
            self._old_cwd: list[str] = []

        def __enter__(self) -> None:
            self._old_cwd.append(os.getcwd())
            os.chdir(self.path)

        def __exit__(self, *excinfo) -> None:
            os.chdir(self._old_cwd.pop())


def _load_version():
    return importlib_metadata.version("tortoise-orm")


def test_version():
    assert _load_version() == __version__


def _run_shell(cmd: str, **kw) -> subprocess.CompletedProcess[str]:
    return subprocess.run(shlex.split(cmd), **kw)  # nosec


def _capture_output(cmd: str) -> str:
    return _run_shell(cmd, text=True, capture_output=True, encoding="utf-8").stdout


def test_added_by_poetry_v2(tmp_path: Path):
    tortoise_orm = Path(__file__).parent.resolve().parent
    py = "{}.{}".format(*sys.version_info)
    poetry = "poetry"
    if shutil.which(poetry) is None:
        poetry = "uvx " + poetry
    with chdir(tmp_path):
        package = "foo"
        _run_shell(f"{poetry} new {package} --python=^{py}")  # nosec
        with chdir(package):
            _run_shell(f"{poetry} config --local virtualenvs.in-project true")  # nosec
            _run_shell(f"{poetry} env use {py}")  # nosec
            r = _run_shell(f"{poetry} add {tortoise_orm}")  # nosec
            assert r.returncode == 0
            out = _capture_output(f"{poetry} run pip list")  # nosec
            assert re.search(rf"tortoise-orm\s*{__version__}", out)
