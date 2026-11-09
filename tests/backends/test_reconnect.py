import asyncio

import pytest

from tests.testmodels import Tournament
from tortoise import connections
from tortoise.contrib.test import requireCapability
from tortoise.transactions import in_transaction


@requireCapability(daemon=True)
@pytest.mark.asyncio
async def test_reconnect(db_isolated):
    """Test reconnection after connection expiry."""
    await Tournament.create(name="1")

    await connections.get("models")._expire_connections()

    await Tournament.create(name="2")

    await connections.get("models")._expire_connections()

    await Tournament.create(name="3")

    assert [f"{a.id}:{a.name}" for a in await Tournament.all()] == ["1:1", "2:2", "3:3"]


@requireCapability(daemon=True, supports_transactions=True)
@pytest.mark.asyncio
async def test_reconnect_transaction_start(db_isolated):
    """Test reconnection at transaction start."""
    async with in_transaction():
        await Tournament.create(name="1")

    await connections.get("models")._expire_connections()

    async with in_transaction():
        await Tournament.create(name="2")

    await connections.get("models")._expire_connections()

    async with in_transaction():
        assert [f"{a.id}:{a.name}" for a in await Tournament.all()] == ["1:1", "2:2"]


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_psycopg_pool_detects_connection_killed_by_the_server(db_isolated):
    """A connection whose backend is killed on the server side looks
    perfectly fine to Python (``conn.closed`` stays ``False``) until
    something actually tries to use it -- exactly like a connection
    silently dropped by the network. The pool's connection-check callback
    (wired up in ``PsycopgClient.create_connection``) must be able to
    detect this and reject the connection, which is what lets ``getconn()``
    replace it instead of handing it to a caller.

    Regression test for https://github.com/tortoise/tortoise-orm/issues/2007
    """
    try:
        import psycopg
    except ImportError:
        pytest.skip("psycopg not installed")

    from tortoise.backends.psycopg.client import PsycopgClient

    client = connections.get("models")
    if not isinstance(client, PsycopgClient):
        pytest.skip("psycopg only")

    pool = client._pool
    conn = await pool.getconn()
    try:
        async with conn.cursor() as cur:
            await cur.execute("SELECT pg_backend_pid()")
            pid = (await cur.fetchone())["pg_backend_pid"]
    finally:
        await pool.putconn(conn)

    killer = await psycopg.AsyncConnection.connect(client._template["conninfo"], autocommit=True)
    try:
        async with killer.cursor() as cur:
            await cur.execute("SELECT pg_terminate_backend(%s)", [pid])
    finally:
        await killer.close()

    # Give the server-side termination a moment to actually land before
    # asserting on it.
    await asyncio.sleep(0.3)

    assert conn.closed is False, (
        "connection should still look alive to Python at this point -- "
        "that's the whole point of the bug this is testing for"
    )

    # The connection is back in the pool, looking healthy, but is actually
    # dead. The next checkout -- triggered here by a completely ordinary
    # ORM call -- must transparently get a working connection instead of
    # this one, not raise psycopg.OperationalError: the connection is closed.
    obj = await Tournament.create(name="after-server-killed-the-connection")
    assert obj.name == "after-server-killed-the-connection"
