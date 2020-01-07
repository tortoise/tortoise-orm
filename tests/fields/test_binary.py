from tests import testmodels
from tortoise.contrib import test
from tortoise.exceptions import ConfigurationError, IntegrityError
from tortoise.fields import BinaryField


class TestBinaryFields(test.TestCase):
    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await testmodels.BinaryFields.create()

    async def test_create(self):
        obj0 = await testmodels.BinaryFields.create(binary=bytes(range(256)) * 500)
        obj = await testmodels.BinaryFields.get(id=obj0.id)
        self.assertEqual(obj.binary, bytes(range(256)) * 500)
        self.assertEqual(obj.binary_null, None)
        await obj.save()
        obj2 = await testmodels.BinaryFields.get(id=obj.id)
        self.assertEqual(obj, obj2)

    async def test_values(self):
        obj0 = await testmodels.BinaryFields.create(
            binary=bytes(range(256)), binary_null=bytes(range(255, -1, -1))
        )
        values = await testmodels.BinaryFields.get(id=obj0.id).values("binary", "binary_null")
        self.assertEqual(values[0]["binary"], bytes(range(256)))
        self.assertEqual(values[0]["binary_null"], bytes(range(255, -1, -1)))

    async def test_values_list(self):
        obj0 = await testmodels.BinaryFields.create(binary=bytes(range(256)))
        values = await testmodels.BinaryFields.get(id=obj0.id).values_list("binary", flat=True)
        self.assertEqual(values[0], bytes(range(256)))

    def test_unique_fail(self):
        with self.assertRaisesRegex(ConfigurationError, "can't be indexed"):
            BinaryField(unique=True)

    def test_index_fail(self):
        with self.assertRaisesRegex(ConfigurationError, "can't be indexed"):
            BinaryField(index=True)
