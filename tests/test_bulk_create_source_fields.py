import os

import pytest
import pytest_asyncio

from tests.testmodels import SourceFields
from tortoise import Model, fields
from tortoise.backends.asyncpg.client import AsyncpgDBClient
from tortoise.backends.mysql.client import MySQLClient
from tortoise.context import tortoise_test_context
from tortoise.contrib.test import requireCapability
from tortoise.contrib.test.condition import NotEQ


class BulkCreateSourceFieldCollision(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=50, source_field="value")
    value = fields.CharField(max_length=50, source_field="stored_value", unique=True)
    defaulted = fields.IntField(source_field="stored_default", db_default=7)


@pytest_asyncio.fixture(scope="module")
async def db_module():
    async with tortoise_test_context(
        modules=[__name__],
        db_url=os.getenv("TORTOISE_TEST_DB", "sqlite://:memory:"),
        app_label="models",
        connection_label="models",
    ) as context:
        yield context


SELECTORS = [
    ("eyedee", "chars"),
    ("sometable_id", "some_chars_table"),
    ("eyedee", "some_chars_table"),
    ("sometable_id", "chars"),
]


@requireCapability(dialect=NotEQ("mssql"))
@pytest.mark.asyncio
@pytest.mark.parametrize("selectors", SELECTORS)
@pytest.mark.parametrize("mixed_pk", [False, True])
async def test_bulk_create_maps_source_fields(db, selectors, mixed_pk):
    conflict_field, update_field = selectors
    original = await SourceFields.create(chars="before", blip="keep")
    objects = [SourceFields(eyedee=original.eyedee, chars="after", blip="changed")]
    if mixed_pk:
        objects.append(SourceFields(chars="new", blip="inserted"))
    query = SourceFields.bulk_create(
        objects, on_conflict=[conflict_field], update_fields=[update_field]
    )

    sql = query.sql()
    assert query.sql() == sql
    await query

    stored = await SourceFields.get(eyedee=original.eyedee)
    assert stored.chars == "after"
    assert stored.blip == "keep"
    assert await SourceFields.all().count() == (2 if mixed_pk else 1)
    if mixed_pk:
        assert await SourceFields.get(chars="new").values("blip") == {"blip": "inserted"}


@pytest.mark.parametrize("client_type", [AsyncpgDBClient, MySQLClient])
@pytest.mark.parametrize("selectors", SELECTORS)
@pytest.mark.parametrize("mixed_pk", [False, True])
def test_bulk_create_source_fields_sql(db, client_type, selectors, mixed_pk):
    client = client_type(
        user="test",
        password="test",
        database="test",
        host="127.0.0.1",
        port=1,
        connection_name="source_fields_sql",
    )
    conflict_field, update_field = selectors
    objects = [SourceFields(eyedee=100, chars="updated")]
    if mixed_pk:
        objects.append(SourceFields(chars="inserted"))
    query = SourceFields.bulk_create(
        objects, using_db=client, on_conflict=[conflict_field], update_fields=[update_field]
    )

    sql = query.sql()
    assert query.sql() == sql
    assert len(sql.split(";")) == (2 if mixed_pk else 1)
    for statement in sql.split(";"):
        if client.capabilities.dialect == "mysql":
            updates = statement.split(" ON DUPLICATE KEY UPDATE ")[1]
            assert updates.startswith("`some_chars_table`=")
            assert updates.count("`some_chars_table`") == 2
            assert "`chars`" not in updates
        else:
            assert (
                ' ON CONFLICT ("sometable_id") DO UPDATE SET '
                '"some_chars_table"=EXCLUDED."some_chars_table"'
            ) in statement


@requireCapability(dialect=NotEQ("mssql"))
@pytest.mark.asyncio
async def test_bulk_create_prefers_model_names_and_keeps_omitted_defaults(db):
    original = await BulkCreateSourceFieldCollision.create(
        name="keep", value="before", defaulted=42
    )
    await BulkCreateSourceFieldCollision.bulk_create(
        [BulkCreateSourceFieldCollision(id=original.id, name="ignored", value="after")],
        on_conflict=["id"],
        update_fields=["value", "defaulted"],
    )

    stored = await BulkCreateSourceFieldCollision.get(id=original.id)
    assert stored.name == "keep"
    assert stored.value == "after"
    assert stored.defaulted == 42


@requireCapability(dialect=NotEQ("mssql"))
@pytest.mark.asyncio
async def test_bulk_create_conflict_target_prefers_model_name(db):
    original = await BulkCreateSourceFieldCollision.create(name="before", value="key")
    await BulkCreateSourceFieldCollision.bulk_create(
        [BulkCreateSourceFieldCollision(name="after", value="key")],
        on_conflict=["value"],
        update_fields=["name"],
    )

    stored = await BulkCreateSourceFieldCollision.get(id=original.id)
    assert stored.name == "after"
    assert stored.value == "key"
    assert await BulkCreateSourceFieldCollision.all().count() == 1


@requireCapability(dialect=NotEQ("mssql"))
@pytest.mark.asyncio
async def test_bulk_create_maps_foreign_key_backing_field(db):
    old_parent = await SourceFields.create(chars="old parent")
    new_parent = await SourceFields.create(chars="new parent")
    original = await SourceFields.create(chars="keep", fk=old_parent)
    await SourceFields.bulk_create(
        [SourceFields(eyedee=original.eyedee, chars="ignored", fk_id=new_parent.eyedee)],
        on_conflict=["sometable_id"],
        update_fields=["fk_id"],
    )

    stored = await SourceFields.get(eyedee=original.eyedee)
    assert stored.chars == "keep"
    assert stored.fk_id == new_parent.eyedee
