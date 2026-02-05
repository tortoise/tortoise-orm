import os
from functools import partial

from tortoise.config import AppConfig, DBUrlConfig, TortoiseConfig
from tortoise.contrib.fastapi import RegisterTortoise

# Single source of truth for Tortoise ORM configuration
TORTOISE_ORM = TortoiseConfig(
    connections={"default": DBUrlConfig(url=os.getenv("DB_URL", "sqlite://db.sqlite3"))},
    apps={
        "models": AppConfig(
            models=["models"],
            default_connection="default",
            migrations="migrations",  # Explicit path since models.py is a file, not a package
        )
    },
)

register_orm = partial(
    RegisterTortoise,
    config=TORTOISE_ORM,
    generate_schemas=True,
)
