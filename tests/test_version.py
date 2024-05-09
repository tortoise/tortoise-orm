import subprocess

from tortoise import __version__


def test_version():
    r = subprocess.run(["poetry", "version", "-s"], capture_output=True)
    r.stdout.decode() == __version__
