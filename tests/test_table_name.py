from tests.testmodels import Tournament
from tortoise import Model
from tortoise.contrib import test


def table_name_generator(model_cls: Model):
    return f"test_{model_cls.__name__.lower()}"


class TestTableNameGenerator(test.TestCase):
    def test_generator_basic(self):
        """Test that table name is correctly generated when using generator"""

        class TestModel(Tournament):
            class Meta:
                table_name_generator = table_name_generator

        self.assertEqual(TestModel._meta.db_table, "test_testmodel")

    def test_explicit_table_precedence(self):
        """Test that explicit table name takes precedence over generator"""

        class ExplicitTableModel(Tournament):
            class Meta:
                table = "explicit_table"
                table_name_generator = table_name_generator

        self.assertEqual(ExplicitTableModel._meta.db_table, "explicit_table")

    def test_default_behavior(self):
        """Test default behavior when no generator or table name is provided"""

        class DefaultModel(Tournament):
            class Meta:
                pass

        self.assertEqual(DefaultModel._meta.db_table, "")
