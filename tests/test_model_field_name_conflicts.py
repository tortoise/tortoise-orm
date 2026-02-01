import unittest

from tortoise import fields
from tortoise.exceptions import ConfigurationError
from tortoise.models import Model


class TestModelFieldNameConflicts(unittest.TestCase):
    def test_field_name_conflicts_with_model_attributes(self) -> None:
        with self.assertRaises(ConfigurationError) as ctx:

            class BadModel(Model):
                save = fields.IntField()  # type: ignore[assignment]
                get_table = fields.IntField()  # type: ignore[assignment]

        message = str(ctx.exception)
        self.assertIn("save", message)
        self.assertIn("get_table", message)
