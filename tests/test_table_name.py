from typing import Type

from tests.testmodels import Tournament
from tortoise import Model
from tortoise.contrib import test
from tortoise.exceptions import ConfigurationError


def generate_table_name(model_cls: Type[Model]):
    return f"test_{model_cls.__name__.lower()}"


class TestTableNameGenerator(test.TestCase):
    def test_generator_basic(self):
        """Test that table name is correctly generated when using generator"""

        class TestModel(Tournament):
            class Meta:
                table_name_generator = generate_table_name

        self.assertEqual(TestModel._meta.db_table, "test_testmodel")

    def test_both_table_and_generator_raises(self):
        """Test that setting both table and generator raises ConfigurationError"""
        with self.assertRaises(ConfigurationError) as context:

            class ConflictModel(Tournament):
                class Meta:
                    table = "explicit_table"
                    table_name_generator = generate_table_name

        self.assertIn("Cannot set both 'table' and 'table_name_generator'", str(context.exception))

    def test_default_behavior(self):
        """Test default behavior when no generator or table name is provided"""

        class DefaultModel(Tournament):
            class Meta:
                pass

        self.assertEqual(DefaultModel._meta.db_table, "")
