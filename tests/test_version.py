import shlex
import subprocess
import sys
from pathlib import Path

from tortoise import __version__

if sys.version_info >= (3, 11):
    import tomllib
    from contextlib import chdir
else:
    import contextlib
    import os

    import tomlkit as tomllib

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


def _read_version():
    text = Path("pyproject.toml").read_text()
    data = tomllib.loads(text)
    return data["project"]["version"]


def test_version():
    assert _read_version() == __version__


def run_shell(cmd: str) -> int:
    r = subprocess.run(shlex.split(cmd))
    return r.returncode


def test_added_by_poetry_v2(tmp_path: Path):
    tortoise_orm = Path(__file__).parent.resolve().parent
    with chdir(tmp_path):
        package = "foo"
        exit_code = run_shell(f"poetry new {package}")
        assert exit_code == 0
        with chdir(package):
            exit_code = run_shell(f"poetry add {tortoise_orm}")
            assert exit_code == 0
