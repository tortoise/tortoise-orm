from datetime import datetime
from typing import List

from tests.testmodels import JSONFields
from tortoise.contrib import test


class TestJSONFunctions(test.TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.created_obj = await JSONFields.create(
            data={
                "test_val": "word1",
                "test_int_val": 123,
                "test_date_val": datetime(1970, 1, 1, 12, 36, 59, 123456),
            }
        )

    async def get_filter(self, **kwargs) -> JSONFields:
        return await JSONFields.get(data__filter=kwargs)

    def match_ids(self, *args: List[JSONFields]):
        for obj in args:
            self.assertEqual(self.created_obj.id, obj.id)

    @test.requireCapability(dialect="postgres")
    async def test_postgres_json_in(self):
        filtered_in = await self.get_filter(test_val__in=["word1", "word2"])
        filtered_not_in = await self.get_filter(test_val__not_in=["word3", "word4"])

        self.match_ids(filtered_in, filtered_not_in)

    @test.requireCapability(dialect="postgres")
    async def test_postgres_json_defaults(self):
        filtered_not = await self.get_filter(test_val__not="word2")
        filtered_isnull = await self.get_filter(test_val__isnull=False)
        filtered_not_isnull = await self.get_filter(test_val__not_isnull=True)

        self.match_ids(filtered_not, filtered_isnull, filtered_not_isnull)

    @test.requireCapability(dialect="postgres")
    async def test_postgres_json_int_comparisons(self):
        filtered_gt = await self.get_filter(test_int_val__gt=100)
        filtered_gte = await self.get_filter(test_int_val__gte=100)
        filtered_lt = await self.get_filter(test_int_val__lt=200)
        filtered_lte = await self.get_filter(test_int_val__lte=200)
        filtered_range = await self.get_filter(test_int_val__range=[100, 200])

        self.match_ids(filtered_gt, filtered_gte, filtered_lt, filtered_lte, filtered_range)

    @test.requireCapability(dialect="postgres")
    async def test_postgres_json_string_comparisons(self):
        filtered_contains = await self.get_filter(test_val__contains="ord")
        filtered_icontains = await self.get_filter(test_val__icontains="OrD")
        filtered_startswith = await self.get_filter(test_val__startswith="wor")
        filtered_istartswith = await self.get_filter(test_val__istartswith="wOr")
        filtered_endswith = await self.get_filter(test_val__endswith="rd1")
        filtered_iendswith = await self.get_filter(test_val__iendswith="Rd1")
        filtered_iexact = await self.get_filter(test_val__iexact="wOrD1")

        self.match_ids(
            filtered_contains,
            filtered_icontains,
            filtered_startswith,
            filtered_istartswith,
            filtered_endswith,
            filtered_iendswith,
            filtered_iexact,
        )

    @test.requireCapability(dialect="postgres")
    async def test_postgres_date_comparisons(self):
        filtered_year = await self.get_filter(test_date_val__year=1970)
        filtered_month = await self.get_filter(test_date_val__month=1)
        filtered_day = await self.get_filter(test_date_val__day=1)
        filtered_hour = await self.get_filter(test_date_val__hour=12)
        filtered_minute = await self.get_filter(test_date_val__minute=36)
        filtered_second = await self.get_filter(test_date_val__second=59.123456)
        filtered_microsecond = await self.get_filter(test_date_val__microsecond=59123456)

        self.match_ids(
            filtered_year,
            filtered_month,
            filtered_day,
            filtered_hour,
            filtered_minute,
            filtered_second,
            filtered_microsecond,
        )
