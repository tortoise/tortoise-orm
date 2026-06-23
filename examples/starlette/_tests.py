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


@pytest.mark.anyio
async def test_app() -> None:
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        # note: you _must_ set `base_url` for relative urls like "/" to work
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            r = await client.get("/")
            assert r.status_code == 200
            assert r.json() == {"users": []}
            assert await Users.all() == []

            r = await client.post("/user/", json={"username": "Iron"})
            assert r.status_code == 201
            assert r.json() == {"user": "Users(id=1, username='Iron')"}
            assert await Users.get(id=1) == await Users.last()

            r = await client.get("/")
            assert r.status_code == 200
            assert r.json() == {"users": ["User 1: Iron"]}
            assert await Users.all() == [await Users.first()]
