# mypy: no-disallow-untyped-decorators
# pylint: disable=E0611,E0401
import multiprocessing
import os
from collections.abc import AsyncGenerator
from concurrent.futures import ProcessPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import anyio
import pytest
import pytz
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from tortoise.contrib.test import MEMORY_SQLITE
from tortoise.fields.data import JSON_LOADS

os.environ["DB_URL"] = MEMORY_SQLITE
try:
    from config import register_orm
    from main import app
    from main_custom_timezone import app as app_east
    from models import Users
    from schemas import User_Pydantic
except ImportError:
    if (cwd := Path.cwd()) == (parent := Path(__file__).parent):
        dirpath = "."
    else:
        dirpath = str(parent.relative_to(cwd))
    print(f"You may need to explicitly declare python path:\n\nexport PYTHONPATH={dirpath}\n")
    raise

ClientManagerType = AsyncGenerator[AsyncClient, None]


@pytest.fixture(scope="module")
def anyio_backend() -> str:
    return "asyncio"


@asynccontextmanager
async def client_manager(app, base_url="http://test", **kw) -> ClientManagerType:
    app.state.testing = True
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=base_url, **kw) as c:
            yield c


@pytest.fixture(scope="module")
async def client() -> ClientManagerType:
    async with client_manager(app) as c:
        yield c


@pytest.fixture(scope="module")
async def client_east() -> ClientManagerType:
    async with client_manager(app_east) as c:
        yield c


class UserTester:
    async def create_user(self, async_client: AsyncClient) -> Users:
        response = await async_client.post("/users", json={"username": "admin"})
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["username"] == "admin"
        assert "id" in data
        user_id = data["id"]

        user_obj = await Users.get(id=user_id)
        assert user_obj.id == user_id
        return user_obj

    async def user_list(self, async_client: AsyncClient) -> tuple[datetime, Users, User_Pydantic]:
        utc_now = datetime.now(pytz.utc)
        user_obj = await Users.create(username="test")
        response = await async_client.get("/users")
        assert response.status_code == 200, response.text
        data = response.json()
        assert isinstance(data, list)
        item = await User_Pydantic.from_tortoise_orm(user_obj)
        assert JSON_LOADS(item.model_dump_json()) in data
        return utc_now, user_obj, item


class TestUser(UserTester):
    @pytest.mark.anyio
    async def test_create_user(self, client: AsyncClient) -> None:  # nosec
        await self.create_user(client)

    @pytest.mark.anyio
    async def test_user_list(self, client: AsyncClient) -> None:  # nosec
        await self.user_list(client)


@pytest.mark.anyio
async def test_404(client: AsyncClient) -> None:
    response = await client.get("/404")
    assert response.status_code == 404, response.text
    data = response.json()
    assert isinstance(data["detail"], str)


@pytest.mark.anyio
async def test_422(client: AsyncClient) -> None:
    response = await client.get("/422")
    assert response.status_code == 422, response.text
    data = response.json()
    assert isinstance(data["detail"], list)
    assert isinstance(data["detail"][0], dict)


class TestUserEast(UserTester):
    timezone = "Asia/Shanghai"
    delta_hours = 8

    @pytest.mark.anyio
    async def test_create_user_east(self, client_east: AsyncClient) -> None:  # nosec
        user_obj = await self.create_user(client_east)
        created_at = user_obj.created_at

        # Verify time zone
        asia_tz = pytz.timezone(self.timezone)
        asia_now = datetime.now(pytz.utc).astimezone(asia_tz)
        assert created_at.hour - asia_now.hour == 0

        # UTC timezone
        utc_tz = pytz.timezone("UTC")
        utc_now = datetime.now(pytz.utc).astimezone(utc_tz)
        assert (created_at.hour - utc_now.hour) in [self.delta_hours, self.delta_hours - 24]

    @pytest.mark.anyio
    async def test_user_list(self, client_east: AsyncClient) -> None:  # nosec
        time, user_obj, item = await self.user_list(client_east)
        created_at = user_obj.created_at
        assert (created_at.hour - time.hour) in [self.delta_hours, self.delta_hours - 24]
        assert item.model_dump()["created_at"].hour == created_at.hour


@pytest.mark.anyio
async def test_404_east(client_east: AsyncClient) -> None:
    response = await client_east.get("/404")
    assert response.status_code == 404, response.text
    data = response.json()
    assert isinstance(data["detail"], str)


@pytest.mark.anyio
async def test_422_east(client_east: AsyncClient) -> None:
    response = await client_east.get("/422")
    assert response.status_code == 422, response.text
    data = response.json()
    assert isinstance(data["detail"], list)
    assert isinstance(data["detail"][0], dict)


def query_without_app(pk: int) -> int:
    async def runner() -> bool:
        async with register_orm():
            return await Users.filter(id__gt=pk).count()

    return anyio.run(runner)


def test_query_without_app():
    multiprocessing.set_start_method("spawn")
    with ProcessPoolExecutor(max_workers=1) as executor:
        future = executor.submit(query_without_app, 0)
        assert future.result() >= 0
