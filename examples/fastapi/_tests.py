# mypy: no-disallow-untyped-decorators
# pylint: disable=E0611,E0401
import pytest
from asgi_lifespan import LifespanManager
from httpx import AsyncClient
from main import app
from models import Users


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
async def client():
    async with LifespanManager(app):
        async with AsyncClient(app=app, base_url="http://test") as c:
            yield c


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
