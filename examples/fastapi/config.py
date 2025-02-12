import os
from functools import partial

from tortoise.contrib.fastapi import RegisterTortoise

register_orm = partial(
    RegisterTortoise,
    db_url=os.getenv("DB_URL", "sqlite://db.sqlite3"),
    modules={"models": ["models"]},
    generate_schemas=True,
)
