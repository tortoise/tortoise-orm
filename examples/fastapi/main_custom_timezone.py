# pylint: disable=E0611,E0401
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from config import register_orm
from fastapi import FastAPI
from routers import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # app startup
    # Disable global fallback since this is the secondary app in tests
    # (main app already uses global fallback). Context is stored in app.state.
    async with register_orm(
        app,
        use_tz=False,
        timezone="Asia/Shanghai",
        add_exception_handlers=True,
        _enable_global_fallback=False,
    ):
        # db connected
        yield
        # app teardown
    # db connections closed


app = FastAPI(title="Tortoise ORM FastAPI example", lifespan=lifespan)
app.include_router(users_router, prefix="")
