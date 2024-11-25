from datetime import datetime
from decimal import Decimal

from tests.testmodels import JSONFields
from tortoise.contrib import test


@test.requireCapability(dialect="postgres")
class TestPostgresJSONFunctions(test.TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.obj = await JSONFields.create(
            data={
                "test_val": "word1",
                "test_int_val": 123,
                "test_date_val": datetime(1970, 1, 1, 12, 36, 59, 123456),
            }
        )

    async def get_obj(self, **kwargs) -> JSONFields:
        return await JSONFields.get(data__filter=kwargs)

    async def test_json_in(self):
        self.assertEqual(await self.get_obj(test_val__in=["word1", "word2"]), self.obj)
        self.assertEqual(await self.get_obj(test_val__not_in=["word3", "word4"]), self.obj)

    async def test_json_defaults(self):
        self.assertEqual(await self.get_obj(test_val__not="word2"), self.obj)
        self.assertEqual(await self.get_obj(test_val__isnull=False), self.obj)
        self.assertEqual(await self.get_obj(test_val__not_isnull=True), self.obj)

    async def test_json_int_comparisons(self):
        self.assertEqual(await self.get_obj(test_int_val__gt=100), self.obj)
        self.assertEqual(await self.get_obj(test_int_val__gte=100), self.obj)
        self.assertEqual(await self.get_obj(test_int_val__lt=200), self.obj)
        self.assertEqual(await self.get_obj(test_int_val__lte=200), self.obj)
        self.assertEqual(await self.get_obj(test_int_val__range=[100, 200]), self.obj)

    async def test_json_string_comparisons(self):
        self.assertEqual(await self.get_obj(test_val__contains="ord"), self.obj)
        self.assertEqual(await self.get_obj(test_val__icontains="OrD"), self.obj)
        self.assertEqual(await self.get_obj(test_val__startswith="wor"), self.obj)
        self.assertEqual(await self.get_obj(test_val__istartswith="wOr"), self.obj)
        self.assertEqual(await self.get_obj(test_val__endswith="rd1"), self.obj)
        self.assertEqual(await self.get_obj(test_val__iendswith="Rd1"), self.obj)
        self.assertEqual(await self.get_obj(test_val__iexact="wOrD1"), self.obj)

    async def test_date_comparisons(self):
        self.assertEqual(await self.get_obj(test_date_val__year=1970), self.obj)
        self.assertEqual(await self.get_obj(test_date_val__month=1), self.obj)
        self.assertEqual(await self.get_obj(test_date_val__day=1), self.obj)
        self.assertEqual(await self.get_obj(test_date_val__hour=12), self.obj)
        self.assertEqual(await self.get_obj(test_date_val__minute=36), self.obj)
        self.assertEqual(await self.get_obj(test_date_val__second=Decimal("59.123456")), self.obj)
        self.assertEqual(await self.get_obj(test_date_val__microsecond=59123456), self.obj)
