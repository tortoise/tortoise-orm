from tests import testmodels_mssql as testmodels
from tortoise.contrib import test
from tortoise.exceptions import IntegrityError, OperationalError
from tortoise.exceptions import ConfigurationError

@test.requireCapability(dialect="mssql")
class TestNVARCHARFields(test.IsolatedTestCase):
    tortoise_test_modules = ["tests.testmodels_mssql"]

    async def test_max_length_missing(self):
        with self.assertRaisesRegex(
            TypeError, "missing 1 required positional argument: 'max_length'"
        ):
            testmodels.NVARCHAR()  # pylint: disable=E1120

    async def test_max_length_bad(self):
        with self.assertRaisesRegex(ConfigurationError, "'max_length' must be >= 1"):
            testmodels.NVARCHAR(max_length=0)

    async def _setUpDB(self) -> None:
        try:
            await super()._setUpDB()
        except OperationalError:
            raise test.SkipTest("Works only with MSSQLServer")

    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await testmodels.NVARCHAR.create()

    async def test_filtering(self):
        testmodels.NVARCHAR.create(nvarchar="سلام").sql()

    async def test_create(self):
        obj0 = await testmodels.NVARCHAR.create(nvarchar="سلام")
        obj = await testmodels.NVARCHAR.get(id=obj0.id)
        self.assertEqual(obj.nvarchar, "سلام")
        self.assertIs(obj.nvarchar_null, None)
        await obj.save()
        obj2 = await testmodels.NVARCHAR.get(id=obj.id)
        self.assertEqual(obj, obj2)

    async def test_update(self):
        obj0 = await testmodels.NVARCHAR.create(nvarchar="سلام")
        await testmodels.NVARCHAR.filter(id=obj0.id).update(nvarchar="non-utf8")
        obj = await testmodels.NVARCHAR.get(id=obj0.id)
        self.assertEqual(obj.nvarchar, "non-utf8")
        self.assertIs(obj.nvarchar_null, None)

    async def test_cast(self):
        obj0 = await testmodels.NVARCHAR.create(nvarchar=33)
        obj = await testmodels.NVARCHAR.get(id=obj0.id)
        self.assertEqual(obj.nvarchar, "33")

    async def test_values(self):
        obj0 = await testmodels.NVARCHAR.create(nvarchar="سلام")
        values = await testmodels.NVARCHAR.get(id=obj0.id).values("nvarchar")
        self.assertEqual(values["nvarchar"], "سلام")

    async def test_values_list(self):
        obj0 = await testmodels.NVARCHAR.create(nvarchar="سلام")
        values = await testmodels.NVARCHAR.get(id=obj0.id).values_list("nvarchar", flat=True)
        self.assertEqual(values, "سلام")

    