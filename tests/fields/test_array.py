from tests import testmodels_postgres as testmodels
from tortoise.contrib import test
from tortoise.exceptions import IntegrityError, OperationalError


@test.requireCapability(dialect="postgres")
class TestArrayFields(test.IsolatedTestCase):
    tortoise_test_modules = ["tests.testmodels_postgres"]

    async def _setUpDB(self) -> None:
        try:
            await super()._setUpDB()
        except OperationalError:
            raise test.SkipTest("Works only with PostgreSQL")

    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await testmodels.ArrayFields.create()

    async def test_create(self):
        obj0 = await testmodels.ArrayFields.create(array=[0])
        obj = await testmodels.ArrayFields.get(id=obj0.id)
        self.assertEqual(obj.array, [0])
        self.assertIs(obj.array_null, None)
        await obj.save()
        obj2 = await testmodels.ArrayFields.get(id=obj.id)
        self.assertEqual(obj, obj2)

    async def test_update(self):
        obj0 = await testmodels.ArrayFields.create(array=[0])
        await testmodels.ArrayFields.filter(id=obj0.id).update(array=[1])
        obj = await testmodels.ArrayFields.get(id=obj0.id)
        self.assertEqual(obj.array, [1])
        self.assertIs(obj.array_null, None)

    async def test_values(self):
        obj0 = await testmodels.ArrayFields.create(array=[0])
        values = await testmodels.ArrayFields.get(id=obj0.id).values("array")
        self.assertEqual(values["array"], [0])

    async def test_values_list(self):
        obj0 = await testmodels.ArrayFields.create(array=[0])
        values = await testmodels.ArrayFields.get(id=obj0.id).values_list("array", flat=True)
        self.assertEqual(values, [0])

    async def test_eq_filter(self):
        obj1 = await testmodels.ArrayFields.create(array=[1, 2, 3])
        obj2 = await testmodels.ArrayFields.create(array=[1, 2])

        found = await testmodels.ArrayFields.filter(array=[1, 2, 3]).first()
        self.assertEqual(found, obj1)

        found = await testmodels.ArrayFields.filter(array=[1, 2]).first()
        self.assertEqual(found, obj2)

    async def test_not_filter(self):
        await testmodels.ArrayFields.create(array=[1, 2, 3])
        obj2 = await testmodels.ArrayFields.create(array=[1, 2])

        found = await testmodels.ArrayFields.filter(array__not=[1, 2, 3]).first()
        self.assertEqual(found, obj2)

    async def test_contains_ints(self):
        obj1 = await testmodels.ArrayFields.create(array=[1, 2, 3])
        obj2 = await testmodels.ArrayFields.create(array=[2, 3])
        await testmodels.ArrayFields.create(array=[4, 5, 6])

        found = await testmodels.ArrayFields.filter(array__contains=[2])
        self.assertEqual(found, [obj1, obj2])

        found = await testmodels.ArrayFields.filter(array__contains=[10])
        self.assertEqual(found, [])

    async def test_contains_smallints(self):
        obj1 = await testmodels.ArrayFields.create(array=[], array_smallint=[1, 2, 3])

        found = await testmodels.ArrayFields.filter(array_smallint__contains=[2]).first()
        self.assertEqual(found, obj1)

    async def test_contains_strs(self):
        obj1 = await testmodels.ArrayFields.create(array_str=["a", "b", "c"], array=[])

        found = await testmodels.ArrayFields.filter(array_str__contains=["a", "b", "c"])
        self.assertEqual(found, [obj1])

        found = await testmodels.ArrayFields.filter(array_str__contains=["a", "b"])
        self.assertEqual(found, [obj1])

        found = await testmodels.ArrayFields.filter(array_str__contains=["a", "b", "c", "d"])
        self.assertEqual(found, [])

    async def test_contained_by_ints(self):
        obj1 = await testmodels.ArrayFields.create(array=[1])
        obj2 = await testmodels.ArrayFields.create(array=[1, 2])
        obj3 = await testmodels.ArrayFields.create(array=[1, 2, 3])

        found = await testmodels.ArrayFields.filter(array__contained_by=[1, 2, 3])
        self.assertEqual(found, [obj1, obj2, obj3])

        found = await testmodels.ArrayFields.filter(array__contained_by=[1, 2])
        self.assertEqual(found, [obj1, obj2])

        found = await testmodels.ArrayFields.filter(array__contained_by=[1])
        self.assertEqual(found, [obj1])

    async def test_contained_by_strs(self):
        obj1 = await testmodels.ArrayFields.create(array_str=["a"], array=[])
        obj2 = await testmodels.ArrayFields.create(array_str=["a", "b"], array=[])
        obj3 = await testmodels.ArrayFields.create(array_str=["a", "b", "c"], array=[])

        found = await testmodels.ArrayFields.filter(array_str__contained_by=["a", "b", "c", "d"])
        self.assertEqual(found, [obj1, obj2, obj3])

        found = await testmodels.ArrayFields.filter(array_str__contained_by=["a", "b"])
        self.assertEqual(found, [obj1, obj2])

        found = await testmodels.ArrayFields.filter(array_str__contained_by=["x", "y", "z"])
        self.assertEqual(found, [])

    async def test_overlap_ints(self):
        obj1 = await testmodels.ArrayFields.create(array=[1, 2, 3])
        obj2 = await testmodels.ArrayFields.create(array=[2, 3, 4])
        obj3 = await testmodels.ArrayFields.create(array=[3, 4, 5])

        found = await testmodels.ArrayFields.filter(array__overlap=[1, 2])
        self.assertEqual(found, [obj1, obj2])

        found = await testmodels.ArrayFields.filter(array__overlap=[4])
        self.assertEqual(found, [obj2, obj3])

        found = await testmodels.ArrayFields.filter(array__overlap=[1, 2, 3, 4, 5])
        self.assertEqual(found, [obj1, obj2, obj3])

    async def test_array_length(self):
        await testmodels.ArrayFields.create(array=[1, 2, 3])
        await testmodels.ArrayFields.create(array=[1])
        await testmodels.ArrayFields.create(array=[1, 2])

        found = await testmodels.ArrayFields.filter(array__len=3).values_list("array", flat=True)
        self.assertEqual(list(found), [[1, 2, 3]])

        found = await testmodels.ArrayFields.filter(array__len=1).values_list("array", flat=True)
        self.assertEqual(list(found), [[1]])

        found = await testmodels.ArrayFields.filter(array__len=0).values_list("array", flat=True)
        self.assertEqual(list(found), [])
