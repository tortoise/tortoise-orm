from tortoise import fields
from tortoise.contrib import test


class TestRequired(test.SimpleTestCase):
    async def test_required_by_default(self):
        self.assertTrue(fields.Field(str).required)

    async def test_if_generated_then_not_required(self):
        self.assertFalse(fields.Field(str, generated=True).required)

    async def test_if_null_then_not_required(self):
        self.assertFalse(fields.Field(str, null=True).required)

    async def test_if_has_non_null_default_then_not_required(self):
        self.assertFalse(fields.Field(str, default="").required)

    async def test_if_null_default_then_required(self):
        self.assertTrue(fields.Field(str, default=None).required)
