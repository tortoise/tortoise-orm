# pylint: disable=E0611,E0401
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from routers import router as users_router

from examples.fastapi.config import register_orm
from tortoise import Tortoise, generate_config
from tortoise.contrib.fastapi import RegisterTortoise


@asynccontextmanager
async def lifespan_test(app: FastAPI) -> AsyncGenerator[None, None]:
    config = generate_config(
        os.getenv("TORTOISE_TEST_DB", "sqlite://:memory:"),
        app_modules={"models": ["models"]},
        testing=True,
        connection_label="models",
    )
    async with RegisterTortoise(
        app=app,
        config=config,
        generate_schemas=True,
        add_exception_handlers=True,
        _create_db=True,
    ):
        # db connected
        yield
        # app teardown
    # db connections closed
    await Tortoise._drop_databases()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    if getattr(app.state, "testing", None):
        async with lifespan_test(app) as _:
            yield
    else:
        # app startup
        async with register_orm(app):
            # db connected
            yield
            # app teardown
        # db connections closed


app = FastAPI(title="Tortoise ORM FastAPI example", lifespan=lifespan)
app.include_router(users_router, prefix="")
