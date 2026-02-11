import os
from functools import partial
from pathlib import Path

from tortoise.config import AppConfig, DBUrlConfig, TortoiseConfig
from tortoise.contrib.fastapi import RegisterTortoise

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_URL = f"sqlite://{BASE_DIR / 'db.sqlite3'}"

# Single source of truth for Tortoise ORM configuration
TORTOISE_ORM = TortoiseConfig(
    connections={"default": DBUrlConfig(url=os.getenv("DB_URL", DEFAULT_DB_URL))},
    apps={
        "models": AppConfig(
            models=["models"],
            default_connection="default",
            migrations="migrations",
        )
    },
)

register_orm = partial(
    RegisterTortoise,
    config=TORTOISE_ORM,
)
