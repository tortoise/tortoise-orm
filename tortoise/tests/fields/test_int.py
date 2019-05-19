from tortoise.contrib import test
from tortoise.exceptions import IntegrityError
from tortoise.tests import testmodels


class TestIntFields(test.TestCase):
    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await testmodels.IntFields.create()

    async def test_create(self):
        obj0 = await testmodels.IntFields.create(intnum=2147483647)
        obj = await testmodels.IntFields.get(id=obj0.id)
        self.assertEqual(obj.intnum, 2147483647)
        self.assertEqual(obj.intnum_null, None)
        await obj.save()
        obj2 = await testmodels.IntFields.get(id=obj.id)
        self.assertEqual(obj, obj2)

        await obj.delete()
        obj = await testmodels.IntFields.filter(id=obj0.id).first()
        self.assertEqual(obj, None)

    async def test_min(self):
        obj0 = await testmodels.IntFields.create(intnum=-2147483648)
        obj = await testmodels.IntFields.get(id=obj0.id)
        self.assertEqual(obj.intnum, -2147483648)
        self.assertEqual(obj.intnum_null, None)
        await obj.save()
        obj2 = await testmodels.IntFields.get(id=obj.id)
        self.assertEqual(obj, obj2)

    async def test_cast(self):
        obj0 = await testmodels.IntFields.create(intnum="3")
        obj = await testmodels.IntFields.get(id=obj0.id)
        self.assertEqual(obj.intnum, 3)

    async def test_values(self):
        obj0 = await testmodels.IntFields.create(intnum=1)
        values = await testmodels.IntFields.get(id=obj0.id).values("intnum")
        self.assertEqual(values[0]["intnum"], 1)

    async def test_values_list(self):
        obj0 = await testmodels.IntFields.create(intnum=1)
        values = await testmodels.IntFields.get(id=obj0.id).values_list("intnum", flat=True)
        self.assertEqual(values[0], 1)


class TestSmallIntFields(test.TestCase):
    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await testmodels.SmallIntFields.create()

    async def test_create(self):
        obj0 = await testmodels.SmallIntFields.create(smallintnum=32767)
        obj = await testmodels.SmallIntFields.get(id=obj0.id)
        self.assertEqual(obj.smallintnum, 32767)
        self.assertEqual(obj.smallintnum_null, None)
        await obj.save()
        obj2 = await testmodels.SmallIntFields.get(id=obj.id)
        self.assertEqual(obj, obj2)

    async def test_min(self):
        obj0 = await testmodels.SmallIntFields.create(smallintnum=-32768)
        obj = await testmodels.SmallIntFields.get(id=obj0.id)
        self.assertEqual(obj.smallintnum, -32768)
        self.assertEqual(obj.smallintnum_null, None)
        await obj.save()
        obj2 = await testmodels.SmallIntFields.get(id=obj.id)
        self.assertEqual(obj, obj2)

    async def test_values(self):
        obj0 = await testmodels.SmallIntFields.create(smallintnum=2)
        values = await testmodels.SmallIntFields.get(id=obj0.id).values("smallintnum")
        self.assertEqual(values[0]["smallintnum"], 2)

    async def test_values_list(self):
        obj0 = await testmodels.SmallIntFields.create(smallintnum=2)
        values = await testmodels.SmallIntFields.get(id=obj0.id).values_list(
            "smallintnum", flat=True
        )
        self.assertEqual(values[0], 2)


class TestBigIntFields(test.TestCase):
    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await testmodels.BigIntFields.create()

    async def test_create(self):
        obj0 = await testmodels.BigIntFields.create(intnum=9223372036854775807)
        obj = await testmodels.BigIntFields.get(id=obj0.id)
        self.assertEqual(obj.intnum, 9223372036854775807)
        self.assertEqual(obj.intnum_null, None)
        await obj.save()
        obj2 = await testmodels.BigIntFields.get(id=obj.id)
        self.assertEqual(obj, obj2)

    async def test_min(self):
        obj0 = await testmodels.BigIntFields.create(intnum=-9223372036854775808)
        obj = await testmodels.BigIntFields.get(id=obj0.id)
        self.assertEqual(obj.intnum, -9223372036854775808)
        self.assertEqual(obj.intnum_null, None)
        await obj.save()
        obj2 = await testmodels.BigIntFields.get(id=obj.id)
        self.assertEqual(obj, obj2)

    async def test_cast(self):
        obj0 = await testmodels.BigIntFields.create(intnum="3")
        obj = await testmodels.BigIntFields.get(id=obj0.id)
        self.assertEqual(obj.intnum, 3)

    async def test_values(self):
        obj0 = await testmodels.BigIntFields.create(intnum=1)
        values = await testmodels.BigIntFields.get(id=obj0.id).values("intnum")
        self.assertEqual(values[0]["intnum"], 1)

    async def test_values_list(self):
        obj0 = await testmodels.BigIntFields.create(intnum=1)
        values = await testmodels.BigIntFields.get(id=obj0.id).values_list("intnum", flat=True)
        self.assertEqual(values[0], 1)
