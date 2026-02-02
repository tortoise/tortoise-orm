from typing import Any, cast

from pypika_tortoise import Table

from tortoise import Tortoise, fields
from tortoise.contrib.test import SimpleTestCase
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


class TestModelGetTable(SimpleTestCase):
    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": [__name__]})
        await Tortoise.generate_schemas()

    async def _tearDownDB(self) -> None:
        await Tortoise.get_connection("default").close()

    def test_get_table_returns_fresh_table(self) -> None:
        table = _get_table(SchemaModel)

        self.assertIsInstance(table, Table)
        self.assertEqual(table.get_table_name(), SchemaModel._meta.db_table)
        self.assertIsNotNone(table._schema)
        assert table._schema is not None
        self.assertEqual(table._schema._name, SchemaModel._meta.schema)
        self.assertIsNot(table, SchemaModel._meta.basetable)
        self.assertIsNot(table, _get_table(SchemaModel))

    def test_get_table_default_schema(self) -> None:
        table = _get_table(DefaultSchemaModel)

        self.assertIsInstance(table, Table)
        self.assertEqual(table.get_table_name(), DefaultSchemaModel._meta.db_table)
        self.assertIsNone(table._schema)
