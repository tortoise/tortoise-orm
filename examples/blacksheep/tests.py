# mypy: no-disallow-untyped-decorators
# pylint: disable=E0611,E0401
import asyncio

import pytest
from blacksheep import JSONContent
from blacksheep.testing import TestClient
from models import Users
from server import app


@pytest.fixture(scope="session")
async def client(api):
    return TestClient(api)


@pytest.fixture(scope="session")
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def api():
    await app.start()
    yield app
    await app.stop()


@pytest.mark.asyncio
async def test_create_user(client: TestClient) -> None:
    username = "john"

    response = await client.post("/", content=JSONContent({"username": username}))
    assert response is not None
    assert response.status == 201

    data = await response.json()
    assert data["username"] == username
    assert "id" in data
    user_id = data["id"]

    user_obj = await Users.get(id=user_id)
    assert str(user_obj.id) == user_id


@pytest.mark.asyncio
async def test_get_uses_list(client: TestClient) -> None:
    username = "john"
    await Users.create(username=username)

    response = await client.get("/")
    assert response is not None
    assert response.status == 200

    data = await response.json()
    assert len(data) == 1

    user_data = data[0]
    assert user_data["username"] == username
    assert "id" in user_data
    user_id = user_data["id"]

    user_obj = await Users.get(id=user_id)
    assert str(user_obj.id) == user_id


@pytest.mark.asyncio
async def test_update_user(client: TestClient) -> None:
    user = await Users.create(username="john")

    username = "john_doe"
    response = await client.put(f"/{user.id}", content=JSONContent({"username": username}))
    assert response is not None
    assert response.status == 200

    data = await response.json()
    assert data["username"] == username
    assert "id" in data
    user_id = data["id"]

    user_obj = await Users.get(id=user_id)
    assert str(user_obj.id) == user_id


@pytest.mark.asyncio
async def test_delete_user(client: TestClient) -> None:
    user = await Users.create(username="john")

    response = await client.delete(f"/{user.id}")
    assert response is not None
    assert response.status == 204

    data = await response.json()
    assert data is None

    assert await Users.filter(id=user.id).exists() is False
