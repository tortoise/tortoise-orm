from datetime import datetime
from decimal import Decimal

from tests.testmodels import JSONFields
from tortoise.contrib import test
from tortoise.exceptions import DoesNotExist


@test.requireCapability(dialect="postgres")
class TestPostgresJSON(test.TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.obj = await JSONFields.create(
            data={
                "val": "word1",
                "int_val": 123,
                "float_val": 123.1,
                "date_val": datetime(1970, 1, 1, 12, 36, 59, 123456),
                "int_list": [1, 2, 3],
                "nested": {
                    "val": "word2",
                    "int_val": 456,
                    "int_list": [4, 5, 6],
                    "date_val": datetime(1970, 1, 1, 12, 36, 59, 123456),
                    "nested": {
                        "val": "word3",
                    },
                },
            }
        )

    async def get_by_data_filter(self, **kwargs) -> JSONFields:
        return await JSONFields.get(data__filter=kwargs)

    async def test_json_in(self):
        self.assertEqual(await self.get_by_data_filter(val__in=["word1", "word2"]), self.obj)
        self.assertEqual(await self.get_by_data_filter(val__not_in=["word3", "word4"]), self.obj)

        with self.assertRaises(DoesNotExist):
            await self.get_by_data_filter(val__in=["doesnotexist"])

    async def test_json_defaults(self):
        self.assertEqual(await self.get_by_data_filter(val__not="word2"), self.obj)
        self.assertEqual(await self.get_by_data_filter(val__isnull=False), self.obj)
        self.assertEqual(await self.get_by_data_filter(val__not_isnull=True), self.obj)

    async def test_json_int_comparisons(self):
        self.assertEqual(await self.get_by_data_filter(int_val=123), self.obj)
        self.assertEqual(await self.get_by_data_filter(int_val__gt=100), self.obj)
        self.assertEqual(await self.get_by_data_filter(int_val__gte=100), self.obj)
        self.assertEqual(await self.get_by_data_filter(int_val__lt=200), self.obj)
        self.assertEqual(await self.get_by_data_filter(int_val__lte=200), self.obj)
        self.assertEqual(await self.get_by_data_filter(int_val__range=[100, 200]), self.obj)

        with self.assertRaises(DoesNotExist):
            await self.get_by_data_filter(int_val__gt=1000)

    async def test_json_float_comparisons(self):
        self.assertEqual(await self.get_by_data_filter(float_val__gt=100.0), self.obj)
        self.assertEqual(await self.get_by_data_filter(float_val__gte=100.0), self.obj)
        self.assertEqual(await self.get_by_data_filter(float_val__lt=200.0), self.obj)
        self.assertEqual(await self.get_by_data_filter(float_val__lte=200.0), self.obj)
        self.assertEqual(await self.get_by_data_filter(float_val__range=[100.0, 200.0]), self.obj)

        with self.assertRaises(DoesNotExist):
            await self.get_by_data_filter(int_val__gt=1000.0)

    async def test_json_string_comparisons(self):
        self.assertEqual(await self.get_by_data_filter(val__contains="ord"), self.obj)
        self.assertEqual(await self.get_by_data_filter(val__icontains="OrD"), self.obj)
        self.assertEqual(await self.get_by_data_filter(val__startswith="wor"), self.obj)
        self.assertEqual(await self.get_by_data_filter(val__istartswith="wOr"), self.obj)
        self.assertEqual(await self.get_by_data_filter(val__endswith="rd1"), self.obj)
        self.assertEqual(await self.get_by_data_filter(val__iendswith="Rd1"), self.obj)
        self.assertEqual(await self.get_by_data_filter(val__iexact="wOrD1"), self.obj)

        with self.assertRaises(DoesNotExist):
            await self.get_by_data_filter(val__contains="doesnotexist")

    async def test_date_comparisons(self):
        self.assertEqual(
            await self.get_by_data_filter(date_val=datetime(1970, 1, 1, 12, 36, 59, 123456)),
            self.obj,
        )
        self.assertEqual(await self.get_by_data_filter(date_val__year=1970), self.obj)
        self.assertEqual(await self.get_by_data_filter(date_val__month=1), self.obj)
        self.assertEqual(await self.get_by_data_filter(date_val__day=1), self.obj)
        self.assertEqual(await self.get_by_data_filter(date_val__hour=12), self.obj)
        self.assertEqual(await self.get_by_data_filter(date_val__minute=36), self.obj)
        self.assertEqual(
            await self.get_by_data_filter(date_val__second=Decimal("59.123456")), self.obj
        )
        self.assertEqual(await self.get_by_data_filter(date_val__microsecond=59123456), self.obj)

    async def test_json_list(self):
        self.assertEqual(await self.get_by_data_filter(int_list__0__gt=0), self.obj)
        self.assertEqual(await self.get_by_data_filter(int_list__0__lt=2), self.obj)

        with self.assertRaises(DoesNotExist):
            await self.get_by_data_filter(int_list__0__range=(20, 30))

    async def test_nested(self):
        self.assertEqual(await self.get_by_data_filter(nested__val="word2"), self.obj)
        self.assertEqual(await self.get_by_data_filter(nested__int_val=456), self.obj)
        self.assertEqual(
            await self.get_by_data_filter(
                nested__date_val=datetime(1970, 1, 1, 12, 36, 59, 123456)
            ),
            self.obj,
        )
        self.assertEqual(await self.get_by_data_filter(nested__val__icontains="orD"), self.obj)
        self.assertEqual(await self.get_by_data_filter(nested__int_val__gte=400), self.obj)
        self.assertEqual(await self.get_by_data_filter(nested__date_val__year=1970), self.obj)
        self.assertEqual(await self.get_by_data_filter(nested__date_val__month=1), self.obj)
        self.assertEqual(await self.get_by_data_filter(nested__date_val__day=1), self.obj)
        self.assertEqual(await self.get_by_data_filter(nested__date_val__hour=12), self.obj)
        self.assertEqual(await self.get_by_data_filter(nested__date_val__minute=36), self.obj)
        self.assertEqual(
            await self.get_by_data_filter(nested__date_val__second=Decimal("59.123456")), self.obj
        )
        self.assertEqual(
            await self.get_by_data_filter(nested__date_val__microsecond=59123456), self.obj
        )
        self.assertEqual(await self.get_by_data_filter(nested__val__iexact="wOrD2"), self.obj)
        self.assertEqual(await self.get_by_data_filter(nested__int_val__lt=500), self.obj)
        self.assertEqual(await self.get_by_data_filter(nested__date_val__year=1970), self.obj)
        self.assertEqual(await self.get_by_data_filter(nested__date_val__month=1), self.obj)
        self.assertEqual(await self.get_by_data_filter(nested__date_val__day=1), self.obj)
        self.assertEqual(await self.get_by_data_filter(nested__date_val__hour=12), self.obj)
        self.assertEqual(await self.get_by_data_filter(nested__date_val__minute=36), self.obj)
        self.assertEqual(
            await self.get_by_data_filter(nested__date_val__second=Decimal("59.123456")), self.obj
        )
        self.assertEqual(
            await self.get_by_data_filter(nested__date_val__microsecond=59123456), self.obj
        )
        self.assertEqual(await self.get_by_data_filter(nested__val__iexact="wOrD2"), self.obj)

    async def test_nested_nested(self):
        self.assertEqual(await self.get_by_data_filter(nested__nested__val="word3"), self.obj)
