from tests import testmodels
from tortoise.contrib import test
from tortoise.exceptions import ConfigurationError, IntegrityError
from tortoise.fields import TextField


class TestTextFields(test.TestCase):
    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await testmodels.TextFields.create()

    async def test_create(self):
        obj0 = await testmodels.TextFields.create(text="baaa" * 32000)
        obj = await testmodels.TextFields.get(id=obj0.id)
        self.assertEqual(obj.text, "baaa" * 32000)
        self.assertEqual(obj.text_null, None)
        await obj.save()
        obj2 = await testmodels.TextFields.get(id=obj.id)
        self.assertEqual(obj, obj2)

    async def test_values(self):
        obj0 = await testmodels.TextFields.create(text="baa")
        values = await testmodels.TextFields.get(id=obj0.id).values("text")
        self.assertEqual(values["text"], "baa")

    async def test_values_list(self):
        obj0 = await testmodels.TextFields.create(text="baa")
        values = await testmodels.TextFields.get(id=obj0.id).values_list("text", flat=True)
        self.assertEqual(values, "baa")

    def test_unique_fail(self):
        msg = "TextField can't be indexed, consider CharField"
        with self.assertRaisesRegex(ConfigurationError, msg):
            with self.assertWarnsRegex(
                DeprecationWarning, "`index` is deprecated, please use `db_index` instead"
            ):
                TextField(index=True)
        with self.assertRaisesRegex(ConfigurationError, msg):
            TextField(db_index=True)

    def test_index_fail(self):
        with self.assertRaisesRegex(ConfigurationError, "can't be indexed, consider CharField"):
            TextField(index=True)

    def test_pk_deprecated(self):
        with self.assertWarnsRegex(
            DeprecationWarning, "TextField as a PrimaryKey is Deprecated, use CharField"
        ):
            TextField(primary_key=True)
