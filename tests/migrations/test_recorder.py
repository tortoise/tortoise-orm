import pytest

from tortoise.backends.base.client import Capabilities
from tortoise.migrations.recorder import MigrationRecorder


class FakeConnection:
    def __init__(self, dialect: str) -> None:
        self.capabilities = Capabilities(dialect)
        self.executed_scripts: list[str] = []
        self.inserts: list[tuple[str, list]] = []
        self.queries: list[tuple[str, list | None]] = []

    async def execute_script(self, query: str) -> None:
        self.executed_scripts.append(query)

    async def execute_insert(self, query: str, values: list) -> int:
        self.inserts.append((query, values))
        return 1

    async def execute_query(self, query: str, values: list | None = None):
        self.queries.append((query, values))
        return None, []


@pytest.mark.asyncio
async def test_recorder_quotes_mysql_identifiers() -> None:
    connection = FakeConnection("mysql")
    recorder = MigrationRecorder(connection)

    await recorder.record_applied("app", "0001_initial")
    await recorder.applied_migrations()

    assert connection.inserts
    insert_query, insert_values = connection.inserts[0]
    assert "INSERT INTO `tortoise_migrations`" in insert_query
    assert "(`app`, `name`, `applied_at`)" in insert_query
    assert "%s" in insert_query
    assert insert_values[0] == "app"
    assert insert_values[1] == "0001_initial"

    assert connection.queries
    select_query = connection.queries[0][0]
    assert "SELECT `app`, `name`" in select_query


@pytest.mark.asyncio
async def test_recorder_quotes_mssql_identifiers() -> None:
    connection = FakeConnection("mssql")
    recorder = MigrationRecorder(connection)

    await recorder.record_unapplied("app", "0001_initial")

    assert connection.queries
    delete_query, delete_values = connection.queries[0]
    assert "DELETE FROM [tortoise_migrations]" in delete_query
    assert "[app] = ?" in delete_query
    assert "[name] = ?" in delete_query
    assert delete_values == ["app", "0001_initial"]


@pytest.mark.asyncio
async def test_recorder_uses_parameterized_insert() -> None:
    """Ensure record_applied uses parameterized queries instead of string interpolation.

    This is critical for MariaDB compatibility \u2014 MariaDB rejects ISO 8601
    datetime strings with timezone info (e.g. '2026-03-04T18:06:51+00:00').
    See https://github.com/tortoise/tortoise-orm/issues/2132
    """
    from datetime import datetime

    connection = FakeConnection("mysql")
    recorder = MigrationRecorder(connection)

    await recorder.record_applied("models", "0001_init")

    assert len(connection.inserts) == 1
    query, values = connection.inserts[0]
    # Query must use placeholders, not inline values
    assert "VALUES (%s, %s, %s)" in query
    assert values[0] == "models"
    assert values[1] == "0001_init"
    assert isinstance(values[2], datetime)


@pytest.mark.asyncio
async def test_recorder_uses_parameterized_delete() -> None:
    """Ensure record_unapplied uses parameterized queries."""
    connection = FakeConnection("mysql")
    recorder = MigrationRecorder(connection)

    await recorder.record_unapplied("models", "0001_init")

    assert len(connection.queries) == 1
    query, values = connection.queries[0]
    assert "WHERE `app` = %s" in query
    assert "`name` = %s" in query
    assert values == ["models", "0001_init"]


@pytest.mark.asyncio
async def test_recorder_postgres_placeholders() -> None:
    connection = FakeConnection("postgres")
    recorder = MigrationRecorder(connection)

    await recorder.record_applied("app", "0001_initial")

    assert len(connection.inserts) == 1
    query, values = connection.inserts[0]
    assert "VALUES ($1, $2, $3)" in query


@pytest.mark.asyncio
async def test_recorder_sqlite_placeholders() -> None:
    connection = FakeConnection("sqlite")
    recorder = MigrationRecorder(connection)

    await recorder.record_applied("app", "0001_initial")
    await recorder.record_unapplied("app", "0001_initial")

    insert_query = connection.inserts[0][0]
    assert "VALUES (?, ?, ?)" in insert_query

    delete_query = connection.queries[0][0]
    assert '"app" = ?' in delete_query
    assert '"name" = ?' in delete_query


@pytest.mark.asyncio
async def test_recorder_oracle_placeholders() -> None:
    connection = FakeConnection("oracle")
    recorder = MigrationRecorder(connection)

    await recorder.record_applied("app", "0001_initial")
    await recorder.record_unapplied("app", "0001_initial")

    insert_query = connection.inserts[0][0]
    assert 'INSERT INTO "tortoise_migrations"' in insert_query
    assert "VALUES (?, ?, ?)" in insert_query

    delete_query = connection.queries[0][0]
    assert '"app" = ?' in delete_query
    assert '"name" = ?' in delete_query
