from typing import Type

from tortoise import Tortoise, fields
from tortoise.contrib.test import SimpleTestCase
from tortoise.models import Model


def table_name_generator(model_cls: Type[Model]):
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


class TestTableNameGenerator(SimpleTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        await Tortoise.init(
            db_url="sqlite://:memory:",
            modules={"models": [__name__]},
            table_name_generator=table_name_generator,
        )
        await Tortoise.generate_schemas()

    async def asyncTearDown(self):
        await Tortoise.close_connections()

    async def test_glabal_name_generator(self):
        self.assertEqual(Tournament._meta.db_table, "test_tournament")

    async def test_custom_table_name_precedence(self):
        self.assertEqual(CustomTable._meta.db_table, "my_custom_table")
