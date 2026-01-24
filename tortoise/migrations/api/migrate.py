from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from tortoise.config import TortoiseConfig


async def migrate(
    *,
    config: dict[str, Any] | TortoiseConfig | None = None,
    config_file: str | None = None,
    app_labels: Sequence[str] | None = None,
    target: str | None = None,
    fake: bool = False,
    dry_run: bool = False,
) -> None:
    """Placeholder for future migration runner."""
    if isinstance(config, TortoiseConfig):
        config = config.to_dict()
    _ = (config, config_file, app_labels, target, fake, dry_run)
    return None
