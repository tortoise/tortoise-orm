# pylint: disable=E0611,E0401
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from config import register_orm
from fastapi import FastAPI
from routers import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # app startup
    async with register_orm(
        app,
        use_tz=False,
        timezone="Asia/Shanghai",
    ):
        # db connected
        yield
        # app teardown
    # db connections closed


app = FastAPI(title="Tortoise ORM FastAPI example", lifespan=lifespan)
app.include_router(users_router, prefix="")
