# mypy: no-disallow-untyped-decorators
# pylint: disable=E0611,E0401
from typing import AsyncGenerator

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from main import app
from models import Users


@pytest.fixture(scope="module")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="module")
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


@pytest.mark.anyio
async def test_create_user(client: AsyncClient) -> None:  # nosec
    response = await client.post("/users", json={"username": "admin"})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["username"] == "admin"
    assert "id" in data
    user_id = data["id"]

    user_obj = await Users.get(id=user_id)
    assert user_obj.id == user_id
