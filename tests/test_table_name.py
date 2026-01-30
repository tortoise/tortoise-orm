import pytest
import pytest_asyncio

from tortoise import fields
from tortoise.context import TortoiseContext
from tortoise.models import Model


def table_name_generator(model_cls: type[Model]):
    return f"test_{model_cls.__name__.lower()}"


class Tournament(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)


class CustomTable(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()

    class Meta:
        table = "my_custom_table"


@pytest_asyncio.fixture
async def table_name_db():
    """Fixture for table name generator tests with in-memory SQLite."""
    ctx = TortoiseContext()
    async with ctx:
        await ctx.init(
            db_url="sqlite://:memory:",
            modules={"models": [__name__]},
            table_name_generator=table_name_generator,
        )
        await ctx.generate_schemas()
        yield ctx


@pytest.mark.asyncio
async def test_glabal_name_generator(table_name_db):
    assert Tournament._meta.db_table == "test_tournament"


@pytest.mark.asyncio
async def test_custom_table_name_precedence(table_name_db):
    assert CustomTable._meta.db_table == "my_custom_table"
