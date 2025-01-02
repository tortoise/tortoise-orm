import asyncio
import random
from decimal import Decimal

from tests.testmodels import BenchmarkFewFields, BenchmarkManyFields


def test_filter_few_fields(benchmark, few_fields_benchmark_dataset):
    loop = asyncio.get_event_loop()
    levels = list(set([o.level for o in few_fields_benchmark_dataset]))

    @benchmark
    def bench():
        async def _bench():
            await BenchmarkFewFields.filter(level__in=random.sample(levels, 5)).limit(5)

        loop.run_until_complete(_bench())


def test_filter_many_filters(benchmark, many_fields_benchmark_dataset):
    loop = asyncio.get_event_loop()
    levels = list(set([o.level for o in many_fields_benchmark_dataset]))

    @benchmark
    def bench():
        async def _bench():
            await BenchmarkManyFields.filter(
                level__in=random.sample(levels, 5),
                col_float1__gt=0,
                col_smallint1=2,
                col_int1__lt=2000001,
                col_bigint1__in=[99999999],
                col_char1__contains="value1",
                col_text1="Moo,Foo,Baa,Waa,Moo,Foo,Baa,Waa,Moo,Foo,Baa,Waa",
                col_decimal1=Decimal("2.2"),
            ).limit(5)

        loop.run_until_complete(_bench())
