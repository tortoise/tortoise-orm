import asyncio
import sys

import pytest

from tests.testmodels import Tournament, UniqueName, UniqueNameRequired
from tortoise import connections
from tortoise.contrib.test import requireCapability
from tortoise.contrib.test.condition import NotEQ
from tortoise.transactions import in_transaction

# =============================================================================
# TestConcurrencyIsolated - uses db_isolated fixture
# =============================================================================


@pytest.mark.asyncio
async def test_concurrency_read_isolated(db_isolated):
    """Test concurrent reads."""
    await Tournament.create(name="Test")
    tour1 = await Tournament.first()
    all_read = await asyncio.gather(*[Tournament.first() for _ in range(100)])
    assert all_read == [tour1 for _ in range(100)]


@pytest.mark.asyncio
async def test_concurrency_create_isolated(db_isolated):
    """Test concurrent creates."""
    all_write = await asyncio.gather(*[Tournament.create(name="Test") for _ in range(100)])
    all_read = await Tournament.all()
    assert set(all_write) == set(all_read)


@pytest.mark.asyncio
async def test_nonconcurrent_get_or_create_isolated(db_isolated):
    """Test non-concurrent get_or_create."""
    unas = [await UniqueName.get_or_create(name="c") for _ in range(10)]
    una_created = [una[1] for una in unas if una[1] is True]
    assert len(una_created) == 1
    for una in unas:
        assert una[0] == unas[0][0]


@pytest.mark.parametrize("method_name", ["update_or_create", "get_or_create"])
@pytest.mark.parametrize(
    "defaults_pair",
    [
        ({"optional": "writer-a"}, {"optional": "writer-b"}),
        ({"optional": "writer-a"}, {"other_optional": "writer-b"}),
    ],
)
@pytest.mark.asyncio
async def test_concurrent_create_applies_defaults(
    db_isolated, monkeypatch, method_name, defaults_pair
):
    """Both callers read a missing row before either attempts the real INSERT."""
    original_create_or_get = UniqueNameRequired._create_or_get
    both_missing = asyncio.Event()
    create_attempts = 0

    async def synchronized_create_or_get(cls, db, defaults, **kwargs):
        nonlocal create_attempts
        create_attempts += 1
        if create_attempts == 2:
            both_missing.set()
        await both_missing.wait()
        return await original_create_or_get(db, defaults, **kwargs)

    monkeypatch.setattr(
        UniqueNameRequired, "_create_or_get", classmethod(synchronized_create_or_get)
    )
    method = getattr(UniqueNameRequired, method_name)
    tasks = [
        asyncio.create_task(method(name="race", defaults=defaults)) for defaults in defaults_pair
    ]
    try:
        results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=30)
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    assert create_attempts == 2
    assert sum(created for _, created in results) == 1
    assert await UniqueNameRequired.filter(name="race").count() == 1
    stored = await UniqueNameRequired.get(name="race")
    if method_name == "update_or_create":
        for defaults, (instance, _) in zip(defaults_pair, results):
            for field, value in defaults.items():
                assert getattr(instance, field) == value
        for defaults, (_, created) in zip(defaults_pair, results):
            if not created:
                for field, value in defaults.items():
                    assert getattr(stored, field) == value
        if "other_optional" in defaults_pair[1]:
            assert stored.optional == "writer-a"
            assert stored.other_optional == "writer-b"
    else:
        winner = next(instance for instance, created in results if created)
        for instance, _ in results:
            assert instance.optional == stored.optional == winner.optional
            assert instance.other_optional == stored.other_optional == winner.other_optional


@pytest.mark.asyncio
async def test_update_or_create_refreshes_after_create_race(db_isolated, monkeypatch):
    """The unlocked conflict lookup must not overwrite another writer's later changes."""
    original_create_or_get = UniqueNameRequired._create_or_get

    async def racing_create_or_get(cls, db, defaults, **kwargs):
        await cls.create(name=kwargs["name"], optional="winner", other_optional="old")
        instance, created = await original_create_or_get(db, defaults, **kwargs)
        assert created is False
        await cls.filter(pk=instance.pk).update(other_optional="concurrent")
        return instance, created

    monkeypatch.setattr(UniqueNameRequired, "_create_or_get", classmethod(racing_create_or_get))
    instance, created = await UniqueNameRequired.update_or_create(
        name="race", defaults={"optional": "loser"}
    )
    assert created is False
    assert instance.optional == "loser"
    assert instance.other_optional == "concurrent"
    stored = await UniqueNameRequired.get(pk=instance.pk)
    assert stored.optional == "loser"
    assert stored.other_optional == "concurrent"


@pytest.mark.asyncio
async def test_update_or_create_retries_deleted_race_winner(db_isolated, monkeypatch):
    """A row deleted after the conflict lookup can be created by the retry."""
    original_create_or_get = UniqueNameRequired._create_or_get
    create_attempts = 0

    async def racing_create_or_get(cls, db, defaults, **kwargs):
        nonlocal create_attempts
        create_attempts += 1
        if create_attempts == 1:
            await cls.create(name=kwargs["name"], optional="winner")
        instance, created = await original_create_or_get(db, defaults, **kwargs)
        if create_attempts == 1:
            assert created is False
            await instance.delete()
        return instance, created

    monkeypatch.setattr(UniqueNameRequired, "_create_or_get", classmethod(racing_create_or_get))
    instance, created = await UniqueNameRequired.update_or_create(
        name="race", defaults={"optional": "retry"}
    )
    assert created is True
    assert create_attempts == 2
    assert instance.optional == "retry"
    assert await UniqueNameRequired.filter(name="race").count() == 1
    assert (await UniqueNameRequired.get(pk=instance.pk)).optional == "retry"


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_update_or_create_race_in_existing_transaction(db_isolated, monkeypatch):
    """Conflict recovery and its UPDATE must remain inside the caller's transaction."""
    original_create_or_get = UniqueNameRequired._create_or_get

    async def racing_create_or_get(cls, db, defaults, **kwargs):
        await cls.create(using_db=db, name=kwargs["name"], optional="winner")
        return await original_create_or_get(db, defaults, **kwargs)

    monkeypatch.setattr(UniqueNameRequired, "_create_or_get", classmethod(racing_create_or_get))
    with pytest.raises(RuntimeError, match="rollback caller transaction"):
        async with in_transaction("models") as connection:
            instance, created = await UniqueNameRequired.update_or_create(
                name="race", defaults={"optional": "loser"}, using_db=connection
            )
            assert created is False
            assert instance.optional == "loser"
            assert (await UniqueNameRequired.get(name="race")).optional == "loser"
            raise RuntimeError("rollback caller transaction")
    assert await UniqueNameRequired.filter(name="race").count() == 0


@pytest.mark.skipif(
    sys.version_info < (3, 7), reason="aiocontextvars backport not handling this well"
)
@requireCapability(dialect=NotEQ("mssql"))
@pytest.mark.asyncio
async def test_concurrent_get_or_create_isolated(db_isolated):
    """Test concurrent get_or_create."""
    unas = await asyncio.gather(*[UniqueName.get_or_create(name="d") for _ in range(10)])
    una_created = [una[1] for una in unas if una[1] is True]
    assert len(una_created) == 1
    for una in unas:
        assert una[0] == unas[0][0]


@pytest.mark.skipif(
    sys.version_info < (3, 7), reason="aiocontextvars backport not handling this well"
)
@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_concurrent_transactions_with_multiple_ops(db_isolated):
    """Test concurrent transactions with multiple operations."""

    async def create_in_transaction():
        async with in_transaction():
            await asyncio.gather(*[Tournament.create(name="Test") for _ in range(100)])

    await asyncio.gather(*[create_in_transaction() for _ in range(10)])
    count = await Tournament.all().count()
    assert count == 1000


@pytest.mark.skipif(
    sys.version_info < (3, 7), reason="aiocontextvars backport not handling this well"
)
@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_concurrent_transactions_with_single_op(db_isolated):
    """Test concurrent transactions with single operation."""

    async def create():
        async with in_transaction():
            await Tournament.create(name="Test")

    await asyncio.gather(*[create() for _ in range(100)])
    count = await Tournament.all().count()
    assert count == 100


@pytest.mark.skipif(
    sys.version_info < (3, 7), reason="aiocontextvars backport not handling this well"
)
@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_nested_concurrent_transactions_with_multiple_ops(db_isolated):
    """Test nested concurrent transactions with multiple operations."""

    async def create_in_transaction():
        async with in_transaction():
            async with in_transaction():
                await asyncio.gather(*[Tournament.create(name="Test") for _ in range(100)])

    await asyncio.gather(*[create_in_transaction() for _ in range(10)])
    count = await Tournament.all().count()
    assert count == 1000


# =============================================================================
# TestConcurrencyTransactioned - uses db fixture (transaction rollback)
# =============================================================================


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_concurrency_read_transactioned(db):
    """Test concurrent reads within transaction."""
    await Tournament.create(name="Test")
    tour1 = await Tournament.first()
    all_read = await asyncio.gather(*[Tournament.first() for _ in range(100)])
    assert all_read == [tour1 for _ in range(100)]


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_concurrency_create_transactioned(db):
    """Test concurrent creates within transaction."""
    all_write = await asyncio.gather(*[Tournament.create(name="Test") for _ in range(100)])
    all_read = await Tournament.all()
    assert set(all_write) == set(all_read)


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_nonconcurrent_get_or_create_transactioned(db):
    """Test non-concurrent get_or_create within transaction."""
    unas = [await UniqueName.get_or_create(name="a") for _ in range(10)]
    una_created = [una[1] for una in unas if una[1] is True]
    assert len(una_created) == 1
    for una in unas:
        assert una[0] == unas[0][0]


# =============================================================================
# TestConcurrentDBConnectionInitialization - tests lazy connection init
# These tests ensure concurrent queries don't cause initialization issues.
# =============================================================================


@pytest.mark.asyncio
async def test_concurrent_queries_lazy_init(db_isolated):
    """Test concurrent queries with lazy connection initialization.

    Tortoise.init is lazy and does not initialize the database connection
    until the first query. This test ensures that concurrent queries do not
    cause initialization issues.
    """
    # The db_isolated fixture already initializes the connection, so we just
    # test that concurrent queries work
    await asyncio.gather(*[connections.get("models").execute_query("SELECT 1") for _ in range(100)])


@pytest.mark.asyncio
async def test_concurrent_transactions_lazy_init(db_isolated):
    """Test concurrent transactions with lazy connection initialization."""

    async def transaction() -> None:
        async with in_transaction():
            await connections.get("models").execute_query("SELECT 1")

    await asyncio.gather(*[transaction() for _ in range(100)])
