# mypy: no-disallow-untyped-decorators
# pylint: disable=E0611,E0401
from typing import Generator

import anyio.abc
import pytest
from fastapi.testclient import TestClient
from main import app
from models import Users

from tortoise.contrib.test import finalizer, initializer


@pytest.fixture(scope="module")
def client() -> Generator:
    initializer(["models"])
    with TestClient(app) as c:
        yield c
    finalizer()


@pytest.fixture(scope="module")
def portal(client: TestClient) -> anyio.abc.BlockingPortal:
    assert client.portal
    return client.portal


def test_create_user(client: TestClient, portal: anyio.abc.BlockingPortal):  # nosec
    response = client.post("/users", json={"username": "admin"})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["username"] == "admin"
    assert "id" in data
    user_id = data["id"]

    async def get_user_by_db():
        user = await Users.get(id=user_id)
        return user

    user_obj = portal.call(get_user_by_db)
    assert user_obj.id == user_id
