# mypy: no-disallow-untyped-decorators
# pylint: disable=E0611,E0401
import datetime
from typing import AsyncGenerator

import pytest
import pytz
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from main import app, app_east
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


@pytest.fixture(scope="module")
async def client_east() -> AsyncGenerator[AsyncClient, None]:
    async with LifespanManager(app_east):
        transport = ASGITransport(app=app_east)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


@pytest.mark.anyio
async def test_create_user_east(client_east: AsyncClient) -> None:  # nosec
    response = await client_east.post("/users_east", json={"username": "admin"})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["username"] == "admin"
    assert "id" in data
    user_id = data["id"]

    user_obj = await Users.get(id=user_id)
    assert user_obj.id == user_id

    # Verify that the time zone is East 8.
    created_at = user_obj.created_at

    # Asia/Shanghai timezone
    asia_tz = pytz.timezone("Asia/Shanghai")
    asia_now = datetime.datetime.now(pytz.utc).astimezone(asia_tz)
    assert created_at.hour - asia_now.hour == 0

    # UTC timezone
    utc_tz = pytz.timezone("UTC")
    utc_now = datetime.datetime.now(pytz.utc).astimezone(utc_tz)
    assert created_at.hour - utc_now.hour == 8
