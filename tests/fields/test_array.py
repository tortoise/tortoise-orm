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

    async def test_contains_ints(self):
        await testmodels.ArrayFields.create(array=[1, 2, 3])
        await testmodels.ArrayFields.create(array=[2, 3])
        await testmodels.ArrayFields.create(array=[4, 5, 6])

        found = await testmodels.ArrayFields.filter(array__contains=[2]).values_list(
            "array", flat=True
        )
        self.assertEqual(list(found), [[1, 2, 3], [2, 3]])

        found = await testmodels.ArrayFields.filter(array__contains=[10]).values_list(
            "array", flat=True
        )
        self.assertEqual(list(found), [])

    async def test_contains_strs(self):
        await testmodels.ArrayFields.create(array_str=["a", "b", "c"], array=[])

        found = await testmodels.ArrayFields.filter(
            array_str__contains=["a", "b", "c"]
        ).values_list("array_str", flat=True)
        self.assertEqual(list(found), [["a", "b", "c"]])

        found = await testmodels.ArrayFields.filter(array_str__contains=["a", "b"]).values_list(
            "array_str", flat=True
        )
        self.assertEqual(list(found), [["a", "b", "c"]])

        found = await testmodels.ArrayFields.filter(
            array_str__contains=["a", "b", "c", "d"]
        ).values_list("array_str", flat=True)
        self.assertEqual(list(found), [])

    async def test_contained_by_ints(self):
        await testmodels.ArrayFields.create(array=[1])
        await testmodels.ArrayFields.create(array=[1, 2])
        await testmodels.ArrayFields.create(array=[1, 2, 3])

        found = await testmodels.ArrayFields.filter(array__contained_by=[1, 2, 3]).values_list(
            "array", flat=True
        )
        self.assertEqual(sorted(list(found)), [[1], [1, 2], [1, 2, 3]])

        found = await testmodels.ArrayFields.filter(array__contained_by=[1, 2]).values_list(
            "array", flat=True
        )
        self.assertEqual(sorted(list(found)), [[1], [1, 2]])

        found = await testmodels.ArrayFields.filter(array__contained_by=[1]).values_list(
            "array", flat=True
        )
        self.assertEqual(list(found), [[1]])

    async def test_contained_by_strs(self):
        await testmodels.ArrayFields.create(array_str=["a"], array=[])
        await testmodels.ArrayFields.create(array_str=["a", "b"], array=[])
        await testmodels.ArrayFields.create(array_str=["a", "b", "c"], array=[])

        found = await testmodels.ArrayFields.filter(
            array_str__contained_by=["a", "b", "c", "d"]
        ).values_list("array_str", flat=True)
        self.assertEqual(sorted(list(found)), [["a"], ["a", "b"], ["a", "b", "c"]])

        found = await testmodels.ArrayFields.filter(array_str__contained_by=["a", "b"]).values_list(
            "array_str", flat=True
        )
        self.assertEqual(sorted(list(found)), [["a"], ["a", "b"]])

        found = await testmodels.ArrayFields.filter(
            array_str__contained_by=["x", "y", "z"]
        ).values_list("array_str", flat=True)
        self.assertEqual(list(found), [])
