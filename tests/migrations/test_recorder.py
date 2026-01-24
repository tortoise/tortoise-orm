import pytest

from tortoise.backends.base.client import Capabilities
from tortoise.migrations.recorder import MigrationRecorder


class FakeConnection:
    def __init__(self, dialect: str) -> None:
        self.capabilities = Capabilities(dialect)
        self.executed: list[str] = []
        self.queries: list[str] = []

    async def execute_script(self, query: str) -> None:
        self.executed.append(query)

    async def execute_query(self, query: str):
        self.queries.append(query)
        return None, []


@pytest.mark.asyncio
async def test_recorder_quotes_mysql_identifiers() -> None:
    connection = FakeConnection("mysql")
    recorder = MigrationRecorder(connection)

    await recorder.record_applied("app", "0001_initial")
    await recorder.applied_migrations()

    assert connection.executed
    assert "INSERT INTO `tortoise_migrations`" in connection.executed[0]
    assert "(`app`, `name`, `applied_at`)" in connection.executed[0]
    assert connection.queries
    assert "SELECT `app`, `name`" in connection.queries[0]


@pytest.mark.asyncio
async def test_recorder_quotes_mssql_identifiers() -> None:
    connection = FakeConnection("mssql")
    recorder = MigrationRecorder(connection)

    await recorder.record_unapplied("app", "0001_initial")

    assert connection.executed
    assert "DELETE FROM [tortoise_migrations]" in connection.executed[0]
    assert "WHERE [app] = 'app'" in connection.executed[0]
