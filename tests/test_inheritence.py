from tests.testmodels import MyAbstractBaseModel, MyDerivedModel
from tortoise.contrib import test


class TestInheritance(test.TestCase):
    async def test_basic(self):
        model = MyDerivedModel(name="test")
        self.assertTrue(hasattr(MyAbstractBaseModel(), "name"))
        self.assertTrue(hasattr(model, "created_at"))
        self.assertTrue(hasattr(model, "modified_at"))
        self.assertTrue(hasattr(model, "name"))
        self.assertTrue(hasattr(model, "first_name"))
        await model.save()
        self.assertIsNotNone(model.created_at)
        self.assertIsNotNone(model.modified_at)
