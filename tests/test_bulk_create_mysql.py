import os

import pytest
import pytest_asyncio

from tests.testmodels import UniqueName
from tortoise.backends.asyncpg.client import AsyncpgDBClient
from tortoise.backends.mysql.client import MySQLClient
from tortoise.context import tortoise_test_context
from tortoise.contrib.test import requireCapability


@pytest_asyncio.fixture(scope="module")
async def db_module():
    """Create only the model used by these backend-specific tests."""
    async with tortoise_test_context(
        modules=[__name__],
        db_url=os.getenv("TORTOISE_TEST_DB", "sqlite://:memory:"),
        app_label="models",
        connection_label="models",
    ) as context:
        yield context


@pytest.fixture
def mysql_sql_client():
    return MySQLClient(
        user="test",
        password="test",
        database="test",
        host="127.0.0.1",
        port=1,
        connection_name="mysql_upsert_sql",
    )


@pytest.mark.parametrize("mixed_pk", [False, True])
@pytest.mark.parametrize("update_fields", [["optional"], ["optional", "other_optional"]])
def test_mysql_bulk_create_uses_values_for_upserts(db, mysql_sql_client, mixed_pk, update_fields):
    objects = [UniqueName(name="new", optional="value")]
    if mixed_pk:
        objects.append(UniqueName(id=100, name="existing", optional="updated"))
    query = UniqueName.bulk_create(
        objects,
        using_db=mysql_sql_client,
        update_fields=update_fields,
        on_conflict=["name"],
    )

    sql = query.sql()

    assert query.sql() == sql
    assert len(sql.split(";")) == (2 if mixed_pk else 1)
    expected_updates = ",".join(f"`{field}`=VALUES(`{field}`)" for field in update_fields)
    for statement in sql.split(";"):
        assert f" ON DUPLICATE KEY UPDATE {expected_updates}" in statement
        assert " AS `new_" not in statement


def test_mysql_bulk_create_ignore_conflicts_keeps_insert_ignore(db, mysql_sql_client):
    query = UniqueName.bulk_create(
        [UniqueName(name="new")], using_db=mysql_sql_client, ignore_conflicts=True
    )

    sql = query.sql()

    assert sql.startswith("INSERT IGNORE INTO `uniquename`")
    assert "ON DUPLICATE KEY UPDATE" not in sql
    assert " AS `new_" not in sql


@pytest.mark.parametrize("mixed_pk", [False, True])
def test_postgres_bulk_create_keeps_excluded_columns(db, mixed_pk):
    client = AsyncpgDBClient(
        user="test",
        password="test",
        database="test",
        host="127.0.0.1",
        port=1,
        connection_name="postgres_upsert_sql",
    )
    objects = [UniqueName(name="new", optional="value")]
    if mixed_pk:
        objects.append(UniqueName(id=100, name="existing", optional="updated"))
    query = UniqueName.bulk_create(
        objects, using_db=client, update_fields=["optional"], on_conflict=["name"]
    )

    for statement in query.sql().split(";"):
        assert ' ON CONFLICT ("name") DO UPDATE SET "optional"=EXCLUDED."optional"' in statement
        assert 'VALUES("optional")' not in statement


@requireCapability(dialect="mysql")
@pytest.mark.asyncio
@pytest.mark.parametrize("batch_size", [None, 1])
@pytest.mark.parametrize("update_both_fields", [False, True])
async def test_mysql_bulk_create_upserts_both_pk_paths(db, batch_size, update_both_fields):
    first = await UniqueName.create(name="first", optional="old", other_optional="keep")
    second = await UniqueName.create(name="second", optional="old", other_optional="keep")
    update_fields = ["optional", "other_optional"] if update_both_fields else ["optional"]

    await UniqueName.bulk_create(
        [
            UniqueName(name=first.name, optional="updated", other_optional="changed"),
            UniqueName(
                id=second.id, name=second.name, optional="updated", other_optional="changed"
            ),
            UniqueName(name="new", optional="inserted", other_optional="new"),
        ],
        batch_size=batch_size,
        update_fields=update_fields,
        on_conflict=["name"],
    )

    other_value = "changed" if update_both_fields else "keep"
    assert await UniqueName.all().order_by("name").values("name", "optional", "other_optional") == [
        {"name": "first", "optional": "updated", "other_optional": other_value},
        {"name": "new", "optional": "inserted", "other_optional": "new"},
        {"name": "second", "optional": "updated", "other_optional": other_value},
    ]
