from unittest.mock import Mock

from tests.testmodels import CharPkModel, Event, Team, Tournament
from tortoise import connections
from tortoise.contrib import test
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


@test.requireCapability(supports_transactions=True)
class TestTransactions(test.IsolatedTestCase):
    """This test case uses IsolatedTestCase to ensure that
    - there is no open transaction before the test starts
    - commits in these tests do not impact other tests
    """

    async def test_transactions(self):
        with self.assertRaises(SomeException):
            async with in_transaction():
                tournament = Tournament(name="Test")
                await tournament.save()
                await Tournament.filter(id=tournament.id).update(name="Updated name")
                saved_event = await Tournament.filter(name="Updated name").first()
                self.assertEqual(saved_event.id, tournament.id)
                raise SomeException("Some error")

        saved_event = await Tournament.filter(name="Updated name").first()
        self.assertIsNone(saved_event)

    async def test_get_or_create_transaction_using_db(self):
        async with in_transaction() as connection:
            obj = await CharPkModel.get_or_create(id="FooMip", using_db=connection)
            self.assertIsNotNone(obj)
            await connection.rollback()

        obj2 = await CharPkModel.filter(id="FooMip").first()
        self.assertIsNone(obj2)

    async def test_consequent_nested_transactions(self):
        async with in_transaction():
            await Tournament.create(name="Test")
            async with in_transaction():
                await Tournament.create(name="Nested 1")
            await Tournament.create(name="Test 2")
            async with in_transaction():
                await Tournament.create(name="Nested 2")

        self.assertEqual(
            set(await Tournament.all().values_list("name", flat=True)),
            set(["Test", "Nested 1", "Test 2", "Nested 2"]),
        )

    async def test_caught_exception_in_nested_transaction(self):
        async with in_transaction():
            tournament = await Tournament.create(name="Test")
            await Tournament.filter(id=tournament.id).update(name="Updated name")
            saved_event = await Tournament.filter(name="Updated name").first()
            self.assertEqual(saved_event.id, tournament.id)
            with self.assertRaises(SomeException):
                async with in_transaction():
                    tournament = await Tournament.create(name="Nested")
                    saved_tournament = await Tournament.filter(name="Nested").first()
                    self.assertEqual(tournament.id, saved_tournament.id)
                    raise SomeException("Some error")

        saved_event = await Tournament.filter(name="Updated name").first()
        self.assertIsNotNone(saved_event)
        not_saved_event = await Tournament.filter(name="Nested").first()
        self.assertIsNone(not_saved_event)

    async def test_nested_tx_do_not_commit(self):
        with self.assertRaises(SomeException):
            async with in_transaction():
                tournament = await Tournament.create(name="Test")
                async with in_transaction():
                    tournament.name = "Nested"
                    await tournament.save()

                raise SomeException("Some error")

        self.assertEqual(await Tournament.filter(id=tournament.id).count(), 0)

    async def test_nested_rollback_does_not_enable_autocommit(self):
        with self.assertRaisesRegex(SomeException, "Error 2"):
            async with in_transaction():
                await Tournament.create(name="Test1")
                with self.assertRaisesRegex(SomeException, "Error 1"):
                    async with in_transaction():
                        await Tournament.create(name="Test2")
                        raise SomeException("Error 1")

                await Tournament.create(name="Test3")
                raise SomeException("Error 2")

        self.assertEqual(await Tournament.all().count(), 0)

    async def test_nested_savepoint_rollbacks(self):
        async with in_transaction():
            await Tournament.create(name="Outer Transaction 1")

            with self.assertRaisesRegex(SomeException, "Inner 1"):
                async with in_transaction():
                    await Tournament.create(name="Inner 1")
                    raise SomeException("Inner 1")

            await Tournament.create(name="Outer Transaction 2")

            with self.assertRaisesRegex(SomeException, "Inner 2"):
                async with in_transaction():
                    await Tournament.create(name="Inner 2")
                    raise SomeException("Inner 2")

            await Tournament.create(name="Outer Transaction 3")

        self.assertEqual(
            await Tournament.all().values_list("name", flat=True),
            ["Outer Transaction 1", "Outer Transaction 2", "Outer Transaction 3"],
        )

    async def test_nested_savepoint_rollback_but_other_succeed(self):
        async with in_transaction():
            await Tournament.create(name="Outer Transaction 1")

            with self.assertRaisesRegex(SomeException, "Inner 1"):
                async with in_transaction():
                    await Tournament.create(name="Inner 1")
                    raise SomeException("Inner 1")

            await Tournament.create(name="Outer Transaction 2")

            async with in_transaction():
                await Tournament.create(name="Inner 2")

            await Tournament.create(name="Outer Transaction 3")

        self.assertEqual(
            await Tournament.all().values_list("name", flat=True),
            ["Outer Transaction 1", "Outer Transaction 2", "Inner 2", "Outer Transaction 3"],
        )

    async def test_three_nested_transactions(self):
        async with in_transaction():
            tournament1 = await Tournament.create(name="Test")
            async with in_transaction():
                tournament2 = await Tournament.create(name="Nested")
                async with in_transaction():
                    tournament3 = await Tournament.create(name="Nested2")

        self.assertEqual(
            await Tournament.filter(
                id__in=[tournament1.id, tournament2.id, tournament3.id]
            ).count(),
            3,
        )

    async def test_transaction_decorator(self):
        @atomic()
        async def bound_to_succeed():
            tournament = Tournament(name="Test")
            await tournament.save()
            await Tournament.filter(id=tournament.id).update(name="Updated name")
            saved_event = await Tournament.filter(name="Updated name").first()
            self.assertEqual(saved_event.id, tournament.id)
            return tournament

        tournament = await bound_to_succeed()
        saved_event = await Tournament.filter(name="Updated name").first()
        self.assertEqual(saved_event.id, tournament.id)

    async def test_transaction_decorator_defined_before_init(self):
        tournament = await atomic_decorated_func()
        saved_event = await Tournament.filter(name="Test").first()
        self.assertEqual(saved_event.id, tournament.id)

    async def test_transaction_decorator_fail(self):
        tournament = await Tournament.create(name="Test")

        @atomic()
        async def bound_to_fall():
            saved_event = await Tournament.filter(name="Test").first()
            self.assertEqual(saved_event.id, tournament.id)
            await Tournament.filter(id=tournament.id).update(name="Updated name")
            saved_event = await Tournament.filter(name="Updated name").first()
            self.assertEqual(saved_event.id, tournament.id)
            raise OperationalError()

        with self.assertRaises(OperationalError):
            await bound_to_fall()
        saved_event = await Tournament.filter(name="Test").first()
        self.assertEqual(saved_event.id, tournament.id)
        saved_event = await Tournament.filter(name="Updated name").first()
        self.assertIsNone(saved_event)

    async def test_transaction_with_m2m_relations(self):
        async with in_transaction():
            tournament = await Tournament.create(name="Test")
            event = await Event.create(name="Test event", tournament=tournament)
            team = await Team.create(name="Test team")
            await event.participants.add(team)

    async def test_transaction_exception_1(self):
        with self.assertRaises(TransactionManagementError):
            async with in_transaction() as connection:
                await connection.rollback()
                await connection.rollback()

    async def test_transaction_exception_2(self):
        with self.assertRaises(TransactionManagementError):
            async with in_transaction() as connection:
                await connection.commit()
                await connection.commit()

    async def test_insert_await_across_transaction_fail(self):
        tournament = Tournament(name="Test")
        query = tournament.save()  # pylint: disable=E1111

        try:
            async with in_transaction():
                await query
                raise KeyError("moo")
        except KeyError:
            pass

        self.assertEqual(await Tournament.all(), [])

    async def test_insert_await_across_transaction_success(self):
        tournament = Tournament(name="Test")
        query = tournament.save()  # pylint: disable=E1111

        async with in_transaction():
            await query

        self.assertEqual(await Tournament.all(), [tournament])

    async def test_update_await_across_transaction_fail(self):
        obj = await Tournament.create(name="Test1")

        query = Tournament.filter(id=obj.id).update(name="Test2")
        try:
            async with in_transaction():
                await query
                raise KeyError("moo")
        except KeyError:
            pass

        self.assertEqual(
            await Tournament.all().values("id", "name"), [{"id": obj.id, "name": "Test1"}]
        )

    async def test_update_await_across_transaction_success(self):
        obj = await Tournament.create(name="Test1")

        query = Tournament.filter(id=obj.id).update(name="Test2")
        async with in_transaction():
            await query

        self.assertEqual(
            await Tournament.all().values("id", "name"), [{"id": obj.id, "name": "Test2"}]
        )

    async def test_delete_await_across_transaction_fail(self):
        obj = await Tournament.create(name="Test1")

        query = Tournament.filter(id=obj.id).delete()
        try:
            async with in_transaction():
                await query
                raise KeyError("moo")
        except KeyError:
            pass

        self.assertEqual(
            await Tournament.all().values("id", "name"), [{"id": obj.id, "name": "Test1"}]
        )

    async def test_delete_await_across_transaction_success(self):
        obj = await Tournament.create(name="Test1")

        query = Tournament.filter(id=obj.id).delete()
        async with in_transaction():
            await query

        self.assertEqual(await Tournament.all(), [])

    async def test_select_await_across_transaction_fail(self):
        try:
            async with in_transaction():
                query = Tournament.all().values("name")
                await Tournament.create(name="Test1")
                result = await query
                raise KeyError("moo")
        except KeyError:
            pass

        self.assertEqual(result, [{"name": "Test1"}])
        self.assertEqual(await Tournament.all(), [])

    async def test_select_await_across_transaction_success(self):
        async with in_transaction():
            query = Tournament.all().values("id", "name")
            obj = await Tournament.create(name="Test1")
            result = await query

        self.assertEqual(result, [{"id": obj.id, "name": "Test1"}])
        self.assertEqual(
            await Tournament.all().values("id", "name"), [{"id": obj.id, "name": "Test1"}]
        )

    async def test_rollback_raising_exception(self):
        """Tests that if a rollback raises an exception, the connection context is restored."""
        conn = connections.get("models")
        with self.assertRaisesRegex(ValueError, "rollback"):
            async with conn._in_transaction() as tx_conn:
                tx_conn.rollback = Mock(side_effect=ValueError("rollback"))
                raise ValueError("initial exception")

        self.assertEqual(connections.get("models"), conn)

    async def test_commit_raising_exception(self):
        """Tests that if a commit raises an exception, the connection context is restored."""
        conn = connections.get("models")
        with self.assertRaisesRegex(ValueError, "commit"):
            async with conn._in_transaction() as tx_conn:
                tx_conn.commit = Mock(side_effect=ValueError("commit"))

        self.assertEqual(connections.get("models"), conn)
