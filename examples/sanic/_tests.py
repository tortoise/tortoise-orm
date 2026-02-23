import re
from pathlib import Path

import pytest
from sanic_testing.reusable import ReusableClient

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
def client():
    sanic_app = main.app

    # make register_tortoise treat this as sanic-testing (ReusableClient doesn't set this flag)
    sanic_app._test_manager = True
    client = ReusableClient(sanic_app)
    with client:
        yield client


def test_basic_test_client(client):
    request, response = client.get("/")
    assert response.status == 200
    assert b'{"users":[' in response.body

    request, response = client.post("/user")
    assert response.status == 200
    assert re.match(rb'{"user":"User \d+: New User"}$', response.body)
