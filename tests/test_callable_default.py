from tests import testmodels
from tortoise.contrib import test


class TestCallableDefault(test.TestCase):
    async def test_default_create(self):
        model = await testmodels.CallableDefault.create()
        self.assertEqual(model.callable_default, "callable_default")
        self.assertEqual(model.async_default, "async_callable_default")

    async def test_default_by_save(self):
        saved_model = testmodels.CallableDefault()
        await saved_model.save()
        self.assertEqual(saved_model.callable_default, "callable_default")
        self.assertEqual(saved_model.async_default, "async_callable_default")

    async def test_async_default_change(self):
        default_change = testmodels.CallableDefault()
        default_change.async_default = "changed"
        await default_change.save()
        self.assertEqual(default_change.async_default, "changed")
