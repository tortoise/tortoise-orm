from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from tortoise import fields, models
from tortoise.context import TortoiseContext, get_current_context
from tortoise.contrib.starlette import TortoiseContextMiddleware, register_tortoise


class StarletteMiddlewareModel(models.Model):
    id = fields.IntField(primary_key=True)


def _register_tortoise(app: Starlette) -> None:
    register_tortoise(
        app,
        db_url="sqlite://:memory:",
        modules={"models": [__name__]},
    )


def _register_tortoise_with_lifespan(app: Starlette) -> None:
    register_tortoise(
        app,
        db_url="sqlite://:memory:",
        modules={"models": [__name__]},
        generate_schemas=True,
    )


async def _context_endpoint(_: Request) -> JSONResponse:
    ctx = get_current_context()
    return JSONResponse({"inited": ctx.inited if ctx is not None else False})


async def _get(client: AsyncClient) -> dict:
    response = await client.get("/")
    assert response.status_code == 200
    return response.json()


@pytest.mark.asyncio
async def test_starlette_register_tortoise_uses_middleware_without_patching_endpoint() -> None:
    route = Route("/", _context_endpoint)
    app = Starlette(routes=[route])
    original_endpoint = route.endpoint

    _register_tortoise(app)

    assert route.endpoint is original_endpoint
    assert any(
        middleware.cls is TortoiseContextMiddleware  # type:ignore[comparison-overlap]
        for middleware in app.user_middleware
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        assert await _get(client) == {"inited": True}


@pytest.mark.asyncio
async def test_starlette_middleware_covers_routes_added_after_register_tortoise() -> None:
    app = Starlette()
    _register_tortoise(app)
    app.add_route("/", _context_endpoint)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        assert await _get(client) == {"inited": True}


@pytest.mark.asyncio
async def test_starlette_middleware_does_not_reuse_unrelated_global_context() -> None:
    unrelated_ctx = TortoiseContext()
    unrelated_ctx.__enter__()
    await unrelated_ctx.init(
        db_url="sqlite://:memory:",
        modules={"models": [__name__]},
        _enable_global_fallback=True,
    )
    unrelated_ctx.__exit__(None, None, None)

    async def endpoint(_: Request) -> JSONResponse:
        return JSONResponse({"unrelated": get_current_context() is unrelated_ctx})

    try:
        app = Starlette(routes=[Route("/", endpoint)])
        _register_tortoise(app)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            assert await _get(client) == {"unrelated": False}
    finally:
        await unrelated_ctx.close_connections()


@pytest.mark.asyncio
async def test_starlette_lifespan_context_is_stored_and_cleared() -> None:
    @asynccontextmanager
    async def lifespan(app: Starlette):
        yield

    app = Starlette(routes=[Route("/", _context_endpoint)], lifespan=lifespan)
    _register_tortoise_with_lifespan(app)

    async with LifespanManager(app):
        assert hasattr(app.state, "_tortoise_context")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            assert await _get(client) == {"inited": True}

    assert not hasattr(app.state, "_tortoise_context")
