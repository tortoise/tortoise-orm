"""Tortoise CLI entry points."""

__all__ = ["main"]


def main() -> None:
    from tortoise.cli.cli import main as cli_main

    cli_main()
