"""
Tests for pytest initializer/finalizer functionality.

This module tests the fix for GitHub issue #1110:
https://github.com/tortoise/tortoise-orm/issues/1110

The issue was that calling initializer() would clear connections,
making the database unusable until _restore_default() was called.
This broke pytest fixtures that expected the DB to be ready after initializer().

NOTE: These tests are skipped when running with pytest-xdist in parallel mode
because they use create_db which resets global state and interferes with other tests.
Run them separately with: pytest tests/contrib/test_pytest_initializer.py -n0
"""

import os
import tempfile

import pytest
import pytest_asyncio

from tortoise import Tortoise
from tortoise.contrib.test import create_db


def is_xdist_worker() -> bool:
    """Check if we're running as an xdist worker."""
    return os.environ.get("PYTEST_XDIST_WORKER") is not None


# Skip the entire module if running in xdist parallel mode
pytestmark = pytest.mark.skipif(
    is_xdist_worker(),
    reason="These tests use create_db which resets global state; run separately with -n0",
)


@pytest.mark.asyncio
class TestAsyncCreateDb:
    """Test the async create_db helper function."""

    async def test_create_db_initializes_properly(self):
        """Test that create_db properly initializes the database."""
        await create_db(["tests.testmodels"], db_url="sqlite://:memory:", app_label="models")
        try:
            assert Tortoise._inited is True
            assert Tortoise.apps is not None

            # Verify we can access models
            from tests.testmodels import Tournament

            tournaments = await Tournament.all()
            assert tournaments == []
        finally:
            await Tortoise._drop_databases()

    async def test_create_db_allows_model_operations(self):
        """Test that after create_db, we can perform model operations."""
        await create_db(["tests.testmodels"], db_url="sqlite://:memory:", app_label="models")
        try:
            from tests.testmodels import Tournament

            # Create
            tournament = await Tournament.create(name="Test Tournament")
            assert tournament.id is not None
            assert tournament.name == "Test Tournament"

            # Read
            fetched = await Tournament.get(id=tournament.id)
            assert fetched.name == "Test Tournament"

            # Update
            fetched.name = "Updated Tournament"
            await fetched.save()
            refetched = await Tournament.get(id=tournament.id)
            assert refetched.name == "Updated Tournament"

            # Delete
            await refetched.delete()
            count = await Tournament.all().count()
            assert count == 0
        finally:
            await Tortoise._drop_databases()


@pytest.mark.asyncio
class TestFileBasedSqliteAsync:
    """Test with file-based SQLite database (async tests)."""

    async def test_file_sqlite_with_create_db(self):
        """Test create_db with file-based SQLite."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            db_url = f"sqlite://{db_path}"
            await create_db(["tests.testmodels"], db_url=db_url, app_label="models")
            try:
                from tests.testmodels import Tournament

                tournament = await Tournament.create(name="File DB Tournament")
                assert tournament.id is not None

                # Verify data persists
                fetched = await Tournament.get(id=tournament.id)
                assert fetched.name == "File DB Tournament"
            finally:
                await Tortoise._drop_databases()
        finally:
            # Cleanup the temp file
            if os.path.exists(db_path):
                os.unlink(db_path)


# ============================================================================
# Tests demonstrating create_db used as part of pytest fixtures
# ============================================================================


@pytest_asyncio.fixture
async def db_fixture():
    """
    Example pytest fixture using create_db.

    This is the recommended pattern for pytest-asyncio users.
    """
    await create_db(["tests.testmodels"], db_url="sqlite://:memory:", app_label="models")
    yield
    await Tortoise._drop_databases()


@pytest.mark.asyncio
class TestCreateDbAsFixture:
    """Test create_db when used as a pytest fixture - the recommended pattern."""

    async def test_fixture_provides_working_db(self, db_fixture):
        """Test that the db_fixture provides a working database."""
        from tests.testmodels import Tournament

        # Verify DB is ready
        assert Tortoise._inited is True
        assert Tortoise.apps is not None

        # Verify we can query
        tournaments = await Tournament.all()
        assert tournaments == []

    async def test_fixture_allows_crud_operations(self, db_fixture):
        """Test that we can perform CRUD operations with the fixture."""
        from tests.testmodels import Event, Tournament

        # Create tournament
        tournament = await Tournament.create(name="Fixture Tournament")
        assert tournament.id is not None

        # Create event linked to tournament
        event = await Event.create(name="Fixture Event", tournament=tournament)
        assert event.event_id is not None

        # Read with relation
        fetched_event = await Event.get(event_id=event.event_id).prefetch_related("tournament")
        assert fetched_event.tournament.name == "Fixture Tournament"

        # Update
        tournament.name = "Updated Fixture Tournament"
        await tournament.save()

        # Verify update
        refetched = await Tournament.get(id=tournament.id)
        assert refetched.name == "Updated Fixture Tournament"

    async def test_fixture_isolates_data_between_tests(self, db_fixture):
        """Test that each test gets a fresh database (data isolation)."""
        from tests.testmodels import Tournament

        # This test runs after test_fixture_allows_crud_operations
        # If isolation works, the database should be empty
        count = await Tournament.all().count()
        assert count == 0, "Database should be empty - fixture should provide isolation"

        # Create some data
        await Tournament.create(name="Isolation Test Tournament")
        count = await Tournament.all().count()
        assert count == 1


@pytest_asyncio.fixture
async def db_fixture_with_data():
    """
    Example fixture that pre-populates the database with test data.

    This pattern is useful when multiple tests need the same initial data.
    """
    await create_db(["tests.testmodels"], db_url="sqlite://:memory:", app_label="models")

    # Pre-populate with test data
    from tests.testmodels import Tournament

    await Tournament.create(name="Pre-populated Tournament 1")
    await Tournament.create(name="Pre-populated Tournament 2")

    yield

    await Tortoise._drop_databases()


@pytest.mark.asyncio
class TestCreateDbFixtureWithData:
    """Test fixtures that pre-populate data."""

    async def test_fixture_provides_prepopulated_data(self, db_fixture_with_data):
        """Test that fixture provides pre-populated data."""
        from tests.testmodels import Tournament

        tournaments = await Tournament.all()
        assert len(tournaments) == 2

        names = {t.name for t in tournaments}
        assert names == {"Pre-populated Tournament 1", "Pre-populated Tournament 2"}

    async def test_can_add_to_prepopulated_data(self, db_fixture_with_data):
        """Test that we can add to pre-populated data."""
        from tests.testmodels import Tournament

        # Add new tournament
        await Tournament.create(name="New Tournament")

        tournaments = await Tournament.all()
        assert len(tournaments) == 3
