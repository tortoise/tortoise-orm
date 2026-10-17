from unittest.mock import Mock

import pytest

from tests.testmodels import CharPkModel, Event, Team, Tournament
from tortoise import connections
from tortoise.contrib.test import requireCapability
from tortoise.exceptions import OperationalError, TransactionManagementError
from tortoise.transactions import atomic, in_transaction, on_commit


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


@pytest.mark.asyncio
async def test_on_commit_outside_transaction(db_isolated):
    """Test on_commit runs the callback immediately outside a transaction."""
    calls = []
    await on_commit(lambda: calls.append("called"))
    assert calls == ["called"]


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_on_commit(db_isolated):
    """Test on_commit callbacks run after the transaction commits."""
    calls = []
    async with in_transaction():
        await Tournament.create(name="Test")
        await on_commit(lambda: calls.append("committed"))
        assert calls == []

    assert calls == ["committed"]


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_on_commit_sync_and_async_callbacks(db_isolated):
    """Test on_commit accepts sync and async callbacks and keeps registration order."""
    calls = []

    async def async_callback():
        calls.append("async")

    async with in_transaction():
        await on_commit(lambda: calls.append("sync"))
        await on_commit(async_callback)
        await on_commit(lambda: calls.append("sync again"))

    assert calls == ["sync", "async", "sync again"]


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_on_commit_rollback(db_isolated):
    """Test on_commit callbacks are dropped when the transaction rolls back."""
    calls = []
    with pytest.raises(SomeException):
        async with in_transaction():
            await on_commit(lambda: calls.append("committed"))
            raise SomeException("Some error")

    assert calls == []


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_on_commit_nested_transaction(db_isolated):
    """Test on_commit callbacks of a nested block wait for the outermost commit."""
    calls = []
    async with in_transaction():
        async with in_transaction():
            await on_commit(lambda: calls.append("inner"))
        assert calls == []
        await on_commit(lambda: calls.append("outer"))

    assert calls == ["inner", "outer"]


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_on_commit_nested_rollback(db_isolated):
    """Test a savepoint rollback only drops the callbacks registered in its block."""
    calls = []
    async with in_transaction():
        await on_commit(lambda: calls.append("before"))
        try:
            async with in_transaction():
                await on_commit(lambda: calls.append("rolled back"))
                raise SomeException("Some error")
        except SomeException:
            pass
        await on_commit(lambda: calls.append("after"))

    assert calls == ["before", "after"]


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_on_commit_nested_rollback_drops_inner_callbacks(db_isolated):
    """Test a savepoint rollback drops callbacks of the blocks nested inside it."""
    calls = []
    async with in_transaction():
        try:
            async with in_transaction():
                async with in_transaction():
                    await on_commit(lambda: calls.append("inner"))
                raise SomeException("Some error")
        except SomeException:
            pass

    assert calls == []


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_on_commit_explicit_commit(db_isolated):
    """Test on_commit callbacks run after an explicit commit, even if the block then raises."""
    calls = []
    with pytest.raises(SomeException):
        async with in_transaction() as connection:
            await on_commit(lambda: calls.append("committed"))
            await connection.commit()
            raise SomeException("Some error")

    assert calls == ["committed"]


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_on_commit_explicit_commit_then_rollback(db_isolated):
    """Test a rollback after an explicit commit is rejected, so on_commit callbacks still run."""
    calls = []
    with pytest.raises(TransactionManagementError):
        async with in_transaction() as connection:
            await Tournament.create(name="Test")
            await on_commit(lambda: calls.append("committed"))
            await connection.commit()
            await connection.rollback()

    assert calls == ["committed"]
    assert await Tournament.filter(name="Test").exists()


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_on_commit_explicit_rollback(db_isolated):
    """Test on_commit callbacks are dropped after an explicit rollback."""
    calls = []
    async with in_transaction() as connection:
        await on_commit(lambda: calls.append("committed"))
        await connection.rollback()

    assert calls == []


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_on_commit_transaction_decorator(db_isolated):
    """Test on_commit callbacks registered in an atomic function run after it returns."""
    calls = []

    @atomic()
    async def create_tournament():
        await Tournament.create(name="Test")
        await on_commit(lambda: calls.append("committed"))
        assert calls == []

    await create_tournament()
    assert calls == ["committed"]


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_on_commit_callback_queries_database(db_isolated):
    """Test on_commit callbacks can query the database once the transaction is closed."""
    names = []

    async def read_names():
        names.extend(await Tournament.all().values_list("name", flat=True))

    async with in_transaction():
        await Tournament.create(name="Test")
        await on_commit(read_names)

    assert names == ["Test"]


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_on_commit_callback_raising_exception(db_isolated):
    """Test a failing on_commit callback does not stop the next ones, then raises in a group."""
    calls = []

    def fail():
        raise SomeException("callback")

    with pytest.RaisesGroup(pytest.RaisesExc(SomeException, match="callback")):
        async with in_transaction():
            await Tournament.create(name="Test")
            await on_commit(fail)
            await on_commit(lambda: calls.append("called"))

    assert calls == ["called"]
    assert await Tournament.all().count() == 1


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_on_commit_callbacks_raising_different_exceptions(db_isolated):
    """Test every exception raised by on_commit callbacks ends up in the group."""

    def fail_sync():
        raise SomeException("sync")

    async def fail_async():
        raise ValueError("async")

    with pytest.RaisesGroup(SomeException, ValueError):
        async with in_transaction():
            await on_commit(fail_sync)
            await on_commit(fail_async)


@pytest.mark.asyncio
async def test_on_commit_outside_transaction_raising_exception(db_isolated):
    """Test a failing on_commit callback outside a transaction raises in a group."""

    def fail():
        raise SomeException("callback")

    with pytest.RaisesGroup(SomeException):
        await on_commit(fail)


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_on_commit_commit_raising_exception(db_isolated):
    """Test on_commit callbacks are dropped when the commit itself fails."""
    calls = []
    conn = connections.get("models")
    with pytest.raises(ValueError, match="commit"):
        async with conn._in_transaction() as tx_conn:
            await on_commit(lambda: calls.append("committed"))
            tx_conn.commit = Mock(side_effect=ValueError("commit"))

    assert calls == []
