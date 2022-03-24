from tests import testmodels
from tortoise.contrib import test
from tortoise.exceptions import IntegrityError


class TestArrayFields(test.TestCase):
    @test.requireCapability(dialect="postgres")
    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await testmodels.ArrayFields.create()

    @test.requireCapability(dialect="postgres")
    async def test_create(self):
        obj0 = await testmodels.ArrayFields.create(array=[0])
        obj = await testmodels.ArrayFields.get(id=obj0.id)
        self.assertEqual(obj.array, [0])
        self.assertIs(obj.array_null, None)
        await obj.save()
        obj2 = await testmodels.ArrayFields.get(id=obj.id)
        self.assertEqual(obj, obj2)

    @test.requireCapability(dialect="postgres")
    async def test_update(self):
        obj0 = await testmodels.ArrayFields.create(array=[0])
        await testmodels.ArrayFields.filter(id=obj0.id).update(array=[1])
        obj = await testmodels.ArrayFields.get(id=obj0.id)
        self.assertEqual(obj.array, [1])
        self.assertIs(obj.array_null, None)

    @test.requireCapability(dialect="postgres")
    async def test_values(self):
        obj0 = await testmodels.ArrayFields.create(array=[0])
        values = await testmodels.ArrayFields.get(id=obj0.id).values("array")
        self.assertEqual(values["array"], [0])

    @test.requireCapability(dialect="postgres")
    async def test_values_list(self):
        obj0 = await testmodels.ArrayFields.create(array=[0])
        values = await testmodels.ArrayFields.get(id=obj0.id).values_list("array", flat=True)
        self.assertEqual(values, [0])
