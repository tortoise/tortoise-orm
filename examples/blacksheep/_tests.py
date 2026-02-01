# mypy: no-disallow-untyped-decorators
# pylint: disable=E0611,E0401
import pytest
import pytest_asyncio
from blacksheep import JSONContent
from blacksheep.testing import TestClient
from models import Users
from server import app


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def client(api):
    return TestClient(api)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def api():
    await app.start()
    yield app
    await app.stop()


@pytest.mark.asyncio
async def test_get_uses_list(client: TestClient) -> None:
    username = "john"
    await Users.create(username=username)

    response = await client.get("/")
    assert response.status == 200  # nosec

    data = await response.json()
    assert len(data) == 1  # nosec

    user_data = data[0]
    assert user_data["username"] == username  # nosec
    user_id = user_data["id"]

    user_obj = await Users.get(id=user_id)
    assert str(user_obj.id) == user_id  # nosec


@pytest.mark.asyncio
async def test_create_user(client: TestClient) -> None:
    username = "john"

    response = await client.post("/", content=JSONContent({"username": username}))
    assert response.status == 201  # nosec

    data = await response.json()
    assert data["username"] == username  # nosec
    user_id = data["id"]

    user_obj = await Users.get(id=user_id)
    assert str(user_obj.id) == user_id  # nosec


@pytest.mark.asyncio
async def test_update_user(client: TestClient) -> None:  # nosec
    user = await Users.create(username="john")

    username = "john_doe"
    response = await client.put(f"/{user.id}", content=JSONContent({"username": username}))
    assert response.status == 200  # nosec

    data = await response.json()
    assert data["username"] == username  # nosec
    user_id = data["id"]

    user_obj = await Users.get(id=user_id)
    assert str(user_obj.id) == user_id  # nosec


@pytest.mark.asyncio
async def test_delete_user(client: TestClient) -> None:
    user = await Users.create(username="john")

    response = await client.delete(f"/{user.id}")
    assert response.status == 204  # nosec

    data = await response.json()
    assert data is None  # nosec

    assert await Users.filter(id=user.id).exists() is False  # nosec
