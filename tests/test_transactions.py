from unittest.mock import Mock

import pytest

from tests.testmodels import CharPkModel, Event, Team, Tournament
from tortoise import connections
from tortoise.contrib.test import requireCapability
from tortoise.exceptions import OperationalError, TransactionManagementError
from tortoise.transactions import atomic, in_transaction


class SomeException(Exception):
    """
    A very specific exception so as to not accidentally catch another exception.
    """


@atomic()
async def atomic_decorated_func():
    tournament = Tournament(name="Test")
    await tournament.save()
    return tournament


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_transactions(db_isolated):
    """Test basic transaction rollback on exception."""
    with pytest.raises(SomeException):
        async with in_transaction():
            tournament = Tournament(name="Test")
            await tournament.save()
            await Tournament.filter(id=tournament.id).update(name="Updated name")
            saved_event = await Tournament.filter(name="Updated name").first()
            assert saved_event.id == tournament.id
            raise SomeException("Some error")

    saved_event = await Tournament.filter(name="Updated name").first()
    assert saved_event is None


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_get_or_create_transaction_using_db(db_isolated):
    """Test get_or_create with explicit connection rollback."""
    async with in_transaction() as connection:
        obj = await CharPkModel.get_or_create(id="FooMip", using_db=connection)
        assert obj is not None
        await connection.rollback()

    obj2 = await CharPkModel.filter(id="FooMip").first()
    assert obj2 is None


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_consequent_nested_transactions(db_isolated):
    """Test consequent nested transactions."""
    async with in_transaction():
        await Tournament.create(name="Test")
        async with in_transaction():
            await Tournament.create(name="Nested 1")
        await Tournament.create(name="Test 2")
        async with in_transaction():
            await Tournament.create(name="Nested 2")

    assert set(await Tournament.all().values_list("name", flat=True)) == {
        "Test",
        "Nested 1",
        "Test 2",
        "Nested 2",
    }


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_caught_exception_in_nested_transaction(db_isolated):
    """Test that caught exception in nested transaction only rolls back inner."""
    async with in_transaction():
        tournament = await Tournament.create(name="Test")
        await Tournament.filter(id=tournament.id).update(name="Updated name")
        saved_event = await Tournament.filter(name="Updated name").first()
        assert saved_event.id == tournament.id
        with pytest.raises(SomeException):
            async with in_transaction():
                tournament = await Tournament.create(name="Nested")
                saved_tournament = await Tournament.filter(name="Nested").first()
                assert tournament.id == saved_tournament.id
                raise SomeException("Some error")

    saved_event = await Tournament.filter(name="Updated name").first()
    assert saved_event is not None
    not_saved_event = await Tournament.filter(name="Nested").first()
    assert not_saved_event is None


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_nested_tx_do_not_commit(db_isolated):
    """Test that nested transactions don't commit if outer fails."""
    with pytest.raises(SomeException):
        async with in_transaction():
            tournament = await Tournament.create(name="Test")
            async with in_transaction():
                tournament.name = "Nested"
                await tournament.save()

            raise SomeException("Some error")

    assert await Tournament.filter(id=tournament.id).count() == 0


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_nested_rollback_does_not_enable_autocommit(db_isolated):
    """Test that nested rollback doesn't enable autocommit."""
    with pytest.raises(SomeException, match="Error 2"):
        async with in_transaction():
            await Tournament.create(name="Test1")
            with pytest.raises(SomeException, match="Error 1"):
                async with in_transaction():
                    await Tournament.create(name="Test2")
                    raise SomeException("Error 1")

            await Tournament.create(name="Test3")
            raise SomeException("Error 2")

    assert await Tournament.all().count() == 0


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_nested_savepoint_rollbacks(db_isolated):
    """Test nested savepoint rollbacks."""
    async with in_transaction():
        await Tournament.create(name="Outer Transaction 1")

        with pytest.raises(SomeException, match="Inner 1"):
            async with in_transaction():
                await Tournament.create(name="Inner 1")
                raise SomeException("Inner 1")

        await Tournament.create(name="Outer Transaction 2")

        with pytest.raises(SomeException, match="Inner 2"):
            async with in_transaction():
                await Tournament.create(name="Inner 2")
                raise SomeException("Inner 2")

        await Tournament.create(name="Outer Transaction 3")

    assert await Tournament.all().values_list("name", flat=True) == [
        "Outer Transaction 1",
        "Outer Transaction 2",
        "Outer Transaction 3",
    ]


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_nested_savepoint_rollback_but_other_succeed(db_isolated):
    """Test nested savepoint rollback while other nested transactions succeed."""
    async with in_transaction():
        await Tournament.create(name="Outer Transaction 1")

        with pytest.raises(SomeException, match="Inner 1"):
            async with in_transaction():
                await Tournament.create(name="Inner 1")
                raise SomeException("Inner 1")

        await Tournament.create(name="Outer Transaction 2")

        async with in_transaction():
            await Tournament.create(name="Inner 2")

        await Tournament.create(name="Outer Transaction 3")

    assert await Tournament.all().values_list("name", flat=True) == [
        "Outer Transaction 1",
        "Outer Transaction 2",
        "Inner 2",
        "Outer Transaction 3",
    ]


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_three_nested_transactions(db_isolated):
    """Test three levels of nested transactions."""
    async with in_transaction():
        tournament1 = await Tournament.create(name="Test")
        async with in_transaction():
            tournament2 = await Tournament.create(name="Nested")
            async with in_transaction():
                tournament3 = await Tournament.create(name="Nested2")

    assert (
        await Tournament.filter(id__in=[tournament1.id, tournament2.id, tournament3.id]).count()
        == 3
    )


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_transaction_decorator(db_isolated):
    """Test @atomic decorator with successful transaction."""

    @atomic()
    async def bound_to_succeed():
        tournament = Tournament(name="Test")
        await tournament.save()
        await Tournament.filter(id=tournament.id).update(name="Updated name")
        saved_event = await Tournament.filter(name="Updated name").first()
        assert saved_event.id == tournament.id
        return tournament

    tournament = await bound_to_succeed()
    saved_event = await Tournament.filter(name="Updated name").first()
    assert saved_event.id == tournament.id


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_transaction_decorator_defined_before_init(db_isolated):
    """Test @atomic decorator defined before Tortoise init."""
    tournament = await atomic_decorated_func()
    saved_event = await Tournament.filter(name="Test").first()
    assert saved_event.id == tournament.id


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_transaction_decorator_fail(db_isolated):
    """Test @atomic decorator with failing transaction."""
    tournament = await Tournament.create(name="Test")

    @atomic()
    async def bound_to_fall():
        saved_event = await Tournament.filter(name="Test").first()
        assert saved_event.id == tournament.id
        await Tournament.filter(id=tournament.id).update(name="Updated name")
        saved_event = await Tournament.filter(name="Updated name").first()
        assert saved_event.id == tournament.id
        raise OperationalError()

    with pytest.raises(OperationalError):
        await bound_to_fall()
    saved_event = await Tournament.filter(name="Test").first()
    assert saved_event.id == tournament.id
    saved_event = await Tournament.filter(name="Updated name").first()
    assert saved_event is None


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_transaction_with_m2m_relations(db_isolated):
    """Test transaction with M2M relations."""
    async with in_transaction():
        tournament = await Tournament.create(name="Test")
        event = await Event.create(name="Test event", tournament=tournament)
        team = await Team.create(name="Test team")
        await event.participants.add(team)


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_transaction_exception_1(db_isolated):
    """Test double rollback raises TransactionManagementError."""
    with pytest.raises(TransactionManagementError):
        async with in_transaction() as connection:
            await connection.rollback()
            await connection.rollback()


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_transaction_exception_2(db_isolated):
    """Test double commit raises TransactionManagementError."""
    with pytest.raises(TransactionManagementError):
        async with in_transaction() as connection:
            await connection.commit()
            await connection.commit()


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_insert_await_across_transaction_fail(db_isolated):
    """Test insert await across transaction that fails."""
    tournament = Tournament(name="Test")
    query = tournament.save()  # pylint: disable=E1111

    try:
        async with in_transaction():
            await query
            raise KeyError("moo")
    except KeyError:
        pass

    assert await Tournament.all() == []


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_insert_await_across_transaction_success(db_isolated):
    """Test insert await across transaction that succeeds."""
    tournament = Tournament(name="Test")
    query = tournament.save()  # pylint: disable=E1111

    async with in_transaction():
        await query

    assert await Tournament.all() == [tournament]


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_update_await_across_transaction_fail(db_isolated):
    """Test update await across transaction that fails."""
    obj = await Tournament.create(name="Test1")

    query = Tournament.filter(id=obj.id).update(name="Test2")
    try:
        async with in_transaction():
            await query
            raise KeyError("moo")
    except KeyError:
        pass

    assert await Tournament.all().values("id", "name") == [{"id": obj.id, "name": "Test1"}]


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_update_await_across_transaction_success(db_isolated):
    """Test update await across transaction that succeeds."""
    obj = await Tournament.create(name="Test1")

    query = Tournament.filter(id=obj.id).update(name="Test2")
    async with in_transaction():
        await query

    assert await Tournament.all().values("id", "name") == [{"id": obj.id, "name": "Test2"}]


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_delete_await_across_transaction_fail(db_isolated):
    """Test delete await across transaction that fails."""
    obj = await Tournament.create(name="Test1")

    query = Tournament.filter(id=obj.id).delete()
    try:
        async with in_transaction():
            await query
            raise KeyError("moo")
    except KeyError:
        pass

    assert await Tournament.all().values("id", "name") == [{"id": obj.id, "name": "Test1"}]


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_delete_await_across_transaction_success(db_isolated):
    """Test delete await across transaction that succeeds."""
    obj = await Tournament.create(name="Test1")

    query = Tournament.filter(id=obj.id).delete()
    async with in_transaction():
        await query

    assert await Tournament.all() == []


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_select_await_across_transaction_fail(db_isolated):
    """Test select await across transaction that fails."""
    try:
        async with in_transaction():
            query = Tournament.all().values("name")
            await Tournament.create(name="Test1")
            result = await query
            raise KeyError("moo")
    except KeyError:
        pass

    assert result == [{"name": "Test1"}]
    assert await Tournament.all() == []


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_select_await_across_transaction_success(db_isolated):
    """Test select await across transaction that succeeds."""
    async with in_transaction():
        query = Tournament.all().values("id", "name")
        obj = await Tournament.create(name="Test1")
        result = await query

    assert result == [{"id": obj.id, "name": "Test1"}]
    assert await Tournament.all().values("id", "name") == [{"id": obj.id, "name": "Test1"}]


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_rollback_raising_exception(db_isolated):
    """Tests that if a rollback raises an exception, the connection context is restored."""
    conn = connections.get("models")
    with pytest.raises(ValueError, match="rollback"):
        async with conn._in_transaction() as tx_conn:
            tx_conn.rollback = Mock(side_effect=ValueError("rollback"))
            raise ValueError("initial exception")

    assert connections.get("models") == conn


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_commit_raising_exception(db_isolated):
    """Tests that if a commit raises an exception, the connection context is restored."""
    conn = connections.get("models")
    with pytest.raises(ValueError, match="commit"):
        async with conn._in_transaction() as tx_conn:
            tx_conn.commit = Mock(side_effect=ValueError("commit"))

    assert connections.get("models") == conn
