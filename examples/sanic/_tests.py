import re
from pathlib import Path

import pytest
from sanic_testing import TestManager

try:
    import main
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


@pytest.fixture
def app():
    sanic_app = main.app
    TestManager(sanic_app)
    return sanic_app


@pytest.mark.anyio
async def test_basic_asgi_client(app):
    request, response = await app.asgi_client.get("/")
    assert response.status == 200
    assert b'{"users":[' in response.body

    request, response = await app.asgi_client.post("/user")
    assert response.status == 200
    assert re.match(rb'{"user":"User \d+: New User"}$', response.body)
