from typing import Any, cast

import pytest_asyncio
from pypika_tortoise import Table

from tortoise import fields
from tortoise.context import tortoise_test_context
from tortoise.models import Model


class SchemaModel(Model):
    id = fields.IntField(pk=True)

    class Meta:
        table = "schema_model"
        schema = "schema_one"


class DefaultSchemaModel(Model):
    id = fields.IntField(pk=True)


def _get_table(model: type[Model]) -> Table:
    return cast(Any, model).get_table()


@pytest_asyncio.fixture
async def model_get_table_db():
    """Fixture for model get_table tests with in-memory SQLite."""
    async with tortoise_test_context(modules=[__name__]) as ctx:
        yield ctx


def test_get_table_returns_fresh_table(model_get_table_db):
    table = _get_table(SchemaModel)

    assert isinstance(table, Table)
    assert table.get_table_name() == SchemaModel._meta.db_table
    assert table._schema is not None
    assert table._schema._name == SchemaModel._meta.schema
    assert table is not SchemaModel._meta.basetable
    assert table is not _get_table(SchemaModel)


def test_get_table_default_schema(model_get_table_db):
    table = _get_table(DefaultSchemaModel)

    assert isinstance(table, Table)
    assert table.get_table_name() == DefaultSchemaModel._meta.db_table
    assert table._schema is None
