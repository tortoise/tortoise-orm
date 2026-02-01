import asyncio

from tests.testmodels import BenchmarkFewFields, DecimalFields
from tortoise.expressions import F
from tortoise.functions import Count


def test_expressions_count(benchmark, few_fields_benchmark_dataset):
    loop = asyncio.get_event_loop()

    @benchmark
    def bench():
        async def _bench():
            await BenchmarkFewFields.annotate(text_count=Count("text"))

        loop.run_until_complete(_bench())


def test_expressions_f(benchmark, create_decimals):
    loop = asyncio.get_event_loop()

    @benchmark
    def bench():
        async def _bench():
            await DecimalFields.annotate(d=F("decimal")).all()

        loop.run_until_complete(_bench())
