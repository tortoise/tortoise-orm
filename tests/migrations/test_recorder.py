import warnings
from datetime import datetime

import pytest
from pypika_tortoise import MySQLQuery, OracleQuery, PostgreSQLQuery, SQLLiteQuery
from pypika_tortoise.dialects import MSSQLQuery

from tortoise.migrations.graph import MigrationKey
from tortoise.migrations.recorder import MigrationRecorder


class FakeConnection:
    def __init__(self, query_class: type) -> None:
        self.query_class = query_class
        self.inserts: list[tuple[str, list]] = []
        self.queries: list[tuple[str, list | None]] = []

    async def execute_insert(self, query: str, values: list) -> int:
        self.inserts.append((query, values))
        return 1

    async def execute_query(self, query: str, values: list | None = None):
        self.queries.append((query, values))
        return None, []


@pytest.mark.asyncio
async def test_recorder_quotes_mysql_identifiers() -> None:
    connection = FakeConnection(MySQLQuery)
    recorder = MigrationRecorder(connection)

    await recorder.record_applied("app", "0001_initial")
    await recorder.applied_migrations()

    assert connection.inserts
    insert_query, insert_values = connection.inserts[0]
    assert "INSERT INTO `tortoise_migrations`" in insert_query
    assert "(`app`,`name`,`applied_at`)" in insert_query
    assert "%s" in insert_query
    assert insert_values[0] == "app"
    assert insert_values[1] == "0001_initial"

    assert connection.queries
    select_query = connection.queries[0][0]
    assert "SELECT `app`,`name`" in select_query


@pytest.mark.asyncio
async def test_recorder_quotes_mssql_identifiers() -> None:
    connection = FakeConnection(MSSQLQuery)
    recorder = MigrationRecorder(connection)

    await recorder.record_unapplied("app", "0001_initial")

    assert connection.queries
    delete_query, delete_values = connection.queries[0]
    assert 'DELETE FROM "tortoise_migrations"' in delete_query
    assert '"app"=? AND "name"=?' in delete_query
    assert delete_values == ["app", "0001_initial"]


@pytest.mark.asyncio
async def test_recorder_uses_parameterized_insert() -> None:
    """Ensure record_applied uses parameterized queries instead of string interpolation.

    This is critical for MariaDB compatibility \u2014 MariaDB rejects ISO 8601
    datetime strings with timezone info (e.g. '2026-03-04T18:06:51+00:00').
    See https://github.com/tortoise/tortoise-orm/issues/2132
    """
    connection = FakeConnection(MySQLQuery)
    recorder = MigrationRecorder(connection)

    await recorder.record_applied("models", "0001_init")

    assert len(connection.inserts) == 1
    query, values = connection.inserts[0]
    # Query must use placeholders, not inline values
    assert "VALUES (%s,%s,%s)" in query
    assert values[0] == "models"
    assert values[1] == "0001_init"
    assert isinstance(values[2], datetime)


@pytest.mark.asyncio
async def test_recorder_uses_parameterized_delete() -> None:
    """Ensure record_unapplied uses parameterized queries."""
    connection = FakeConnection(MySQLQuery)
    recorder = MigrationRecorder(connection)

    await recorder.record_unapplied("models", "0001_init")

    assert len(connection.queries) == 1
    query, values = connection.queries[0]
    assert "WHERE `app`=%s AND `name`=%s" in query
    assert values == ["models", "0001_init"]


@pytest.mark.asyncio
async def test_recorder_postgres_placeholders() -> None:
    connection = FakeConnection(PostgreSQLQuery)
    recorder = MigrationRecorder(connection)

    await recorder.record_applied("app", "0001_initial")

    assert len(connection.inserts) == 1
    query, values = connection.inserts[0]
    assert "VALUES ($1,$2,$3)" in query


@pytest.mark.asyncio
async def test_recorder_sqlite_placeholders() -> None:
    connection = FakeConnection(SQLLiteQuery)
    recorder = MigrationRecorder(connection)

    await recorder.record_applied("app", "0001_initial")
    await recorder.record_unapplied("app", "0001_initial")

    insert_query = connection.inserts[0][0]
    assert "VALUES (?,?,?)" in insert_query

    delete_query = connection.queries[0][0]
    assert '"app"=? AND "name"=?' in delete_query


def test_recorder_model_emits_no_field_deprecation_warnings() -> None:
    """Regression: the migration recorder must not trip tortoise's own
    ``pk``/``index`` field deprecation warnings. It builds its bookkeeping
    model internally, so downstream projects can't silence them.
    """
    with warnings.catch_warnings(record=True) as caught:
        # Reset filters so the repo-wide ``ignore:`pk` deprecation`` filter in
        # pyproject.toml doesn't mask a regression here.
        warnings.simplefilter("always")
        MigrationRecorder(FakeConnection(SQLLiteQuery))

    messages = [str(w.message) for w in caught if issubclass(w.category, DeprecationWarning)]
    assert not any("`pk` is deprecated" in m for m in messages), messages
    assert not any("`index` is deprecated" in m for m in messages), messages


@pytest.mark.asyncio
async def test_recorder_oracle_placeholders() -> None:
    connection = FakeConnection(OracleQuery)
    recorder = MigrationRecorder(connection)

    await recorder.record_applied("app", "0001_initial")
    await recorder.record_unapplied("app", "0001_initial")

    insert_query = connection.inserts[0][0]
    assert 'INSERT INTO "tortoise_migrations"' in insert_query
    assert "VALUES (?,?,?)" in insert_query

    delete_query = connection.queries[0][0]
    assert '"app"=? AND "name"=?' in delete_query


@pytest.mark.asyncio
async def test_recorder_round_trips_on_real_database(db_isolated) -> None:
    from tortoise.migrations.executor import MigrationExecutor

    executor = MigrationExecutor(db_isolated.db(), {})
    recorder = executor.recorder
    await recorder.ensure_schema(executor._schema_editor(atomic=False))

    await recorder.record_applied("app", "0001_initial")
    assert await recorder.applied_migrations() == [MigrationKey("app", "0001_initial")]

    await recorder.record_unapplied("app", "0001_initial")
    assert await recorder.applied_migrations() == []


@pytest.mark.asyncio
async def test_recorder_psycopg_placeholders() -> None:
    psycopg_client = pytest.importorskip("tortoise.backends.psycopg.client")
    connection = FakeConnection(psycopg_client.PsycopgSQLQuery)
    recorder = MigrationRecorder(connection)

    await recorder.record_applied("app", "0001_initial")
    await recorder.record_unapplied("app", "0001_initial")

    assert "VALUES (%s,%s,%s)" in connection.inserts[0][0]
    assert '"app"=%s AND "name"=%s' in connection.queries[0][0]
