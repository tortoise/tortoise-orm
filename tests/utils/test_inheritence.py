from tests.testmodels import MyAbstractBaseModel, MyDerivedModel
from tortoise.contrib import test


class TestInheritance(test.SimpleTestCase):
    async def test_basic(self):
        self.assertTrue(hasattr(MyAbstractBaseModel(), "name"))
        self.assertTrue(hasattr(MyDerivedModel(), "created_at"))
        self.assertTrue(hasattr(MyDerivedModel(), "modified_at"))
        self.assertTrue(hasattr(MyDerivedModel(), "name"))
        self.assertTrue(hasattr(MyDerivedModel(), "first_name"))
