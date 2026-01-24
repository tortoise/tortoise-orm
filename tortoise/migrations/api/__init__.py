"""Migration API stubs (experimental)."""

from tortoise.migrations.api.migrate import migrate  # noqa: F401
from tortoise.migrations.api.plan import plan  # noqa: F401

__all__ = ["migrate", "plan"]
