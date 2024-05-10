import sys
from pathlib import Path

from tortoise import __version__

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomlkit as tomllib


def _read_version():
    text = Path("pyproject.toml").read_text()
    data = tomllib.loads(text)
    return data["tool"]["poetry"]["version"]


def test_version():
    assert _read_version() == __version__
