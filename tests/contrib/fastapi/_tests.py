# mypy: no-disallow-untyped-decorators
# pylint: disable=E0611,E0401
import os

import pytest
from asgi_lifespan import LifespanManager
from httpx import AsyncClient
from main import LOG_FILE, app
from models import Users


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
async def client():
    if LOG_FILE.exists():
        LOG_FILE.unlink()
    async with LifespanManager(app):
        async with AsyncClient(app=app, base_url="http://test") as c:
            yield c
    assert not LOG_FILE.exists()


@pytest.mark.anyio
async def test_create_user(client: AsyncClient):  # nosec
    response = await client.post("/users", json={"username": "admin"})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["username"] == "admin"
    assert "id" in data
    user_id = data["id"]

    user_obj = await Users.get(id=user_id)
    assert user_obj.id == user_id


@pytest.mark.anyio
async def test_lifespan(client: AsyncClient):  # nosec
    if os.getenv("USE_LIFESPAN"):
        assert LOG_FILE.exists()
