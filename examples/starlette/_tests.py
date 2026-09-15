# mypy: no-disallow-untyped-decorators
# pylint: disable=E0611,E0401
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

try:
    from main import app
    from models import Users
except ImportError:
    if (cwd := Path.cwd()) == (parent := Path(__file__).parent):
        dirpath = "."
    else:
        dirpath = str(parent.relative_to(cwd))
    print(f"You may need to explicitly declare python path:\n\nexport PYTHONPATH={dirpath}\n")
    raise


@pytest.fixture(scope="module")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="module")
async def client() -> AsyncGenerator[AsyncClient]:
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


@pytest.mark.anyio
async def test_users(client: AsyncClient) -> None:
    await Users.all().delete()
    response = await client.get("/")
    assert response.status_code == 200, response.text
    assert response.json() == {"users": []}
    #    return f"User {self.id}: {self.username}"


@pytest.mark.anyio
async def test_create_user(client: AsyncClient) -> None:
    response = await client.post("/user", json={"username": "admin"})
    assert response.status_code == 201, response.text
    data = response.json()
    assert data == {"user": "User 1: admin"}
    user_obj = await Users.last()
    assert user_obj is not None
    assert user_obj.username == "admin"
    response = await client.get("/")
    assert response.status_code == 200, response.text
    assert response.json() == {"users": [str(user_obj)]}
