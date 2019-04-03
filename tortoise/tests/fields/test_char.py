from tortoise import fields
from tortoise.contrib import test
from tortoise.exceptions import ConfigurationError, IntegrityError
from tortoise.tests import testmodels


class TestCharFields(test.TestCase):
    def test_max_length_missing(self):
        with self.assertRaisesRegex(
            TypeError, "missing 1 required positional argument: 'max_length'"
        ):
            fields.CharField()  # pylint: disable=E1120

    def test_max_length_bad(self):
        with self.assertRaisesRegex(ConfigurationError, "'max_length' must be >= 1"):
            fields.CharField(max_length=0)

    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await testmodels.CharFields.create()

    async def test_create(self):
        obj0 = await testmodels.CharFields.create(char="moo")
        obj = await testmodels.CharFields.get(id=obj0.id)
        self.assertEqual(obj.char, "moo")
        self.assertEqual(obj.char_null, None)
        await obj.save()
        obj2 = await testmodels.CharFields.get(id=obj.id)
        self.assertEqual(obj, obj2)

    async def test_cast(self):
        obj0 = await testmodels.CharFields.create(char=33)
        obj = await testmodels.CharFields.get(id=obj0.id)
        self.assertEqual(obj.char, "33")

    async def test_values(self):
        obj0 = await testmodels.CharFields.create(char="moo")
        values = await testmodels.CharFields.get(id=obj0.id).values("char")
        self.assertEqual(values[0]["char"], "moo")

    async def test_values_list(self):
        obj0 = await testmodels.CharFields.create(char="moo")
        values = await testmodels.CharFields.get(id=obj0.id).values_list("char", flat=True)
        self.assertEqual(values[0], "moo")


class TestTextFields(test.TestCase):
    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await testmodels.TextFields.create()

    async def test_create(self):
        obj0 = await testmodels.TextFields.create(text="baa")
        obj = await testmodels.TextFields.get(id=obj0.id)
        self.assertEqual(obj.text, "baa")
        self.assertEqual(obj.text_null, None)
        await obj.save()
        obj2 = await testmodels.TextFields.get(id=obj.id)
        self.assertEqual(obj, obj2)

    async def test_values(self):
        obj0 = await testmodels.TextFields.create(text="baa")
        values = await testmodels.TextFields.get(id=obj0.id).values("text")
        self.assertEqual(values[0]["text"], "baa")

    async def test_values_list(self):
        obj0 = await testmodels.TextFields.create(text="baa")
        values = await testmodels.TextFields.get(id=obj0.id).values_list("text", flat=True)
        self.assertEqual(values[0], "baa")
