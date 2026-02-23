# pylint: disable=E0611,E0401
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from config import register_orm
from fastapi import FastAPI
from routers import router as users_router

from tortoise.contrib.fastapi import tortoise_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    async with register_orm(app):
        # db connected
        yield
        # app teardown
    # db connections closed


app = FastAPI(
    title="Tortoise ORM FastAPI example",
    lifespan=lifespan,
    exception_handlers=tortoise_exception_handlers(),
)
app.include_router(users_router, prefix="")
