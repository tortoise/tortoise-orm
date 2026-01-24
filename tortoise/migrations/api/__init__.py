"""Migration API (experimental).

Integration note: the migration API initializes apps without eagerly creating
database clients by calling ``Tortoise.init(..., init_connections=False)``.
Connections are created lazily when the executor requests them.
"""

from tortoise.migrations.api.migrate import migrate  # noqa: F401
from tortoise.migrations.api.plan import plan  # noqa: F401

__all__ = ["migrate", "plan"]
