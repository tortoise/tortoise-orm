import asyncio
import random

from tests.testmodels import BenchmarkFewFields


def test_filter_few_fields(benchmark, few_fields_benchmark_dataset):
    loop = asyncio.get_event_loop()
    levels = list(set([o.level for o in few_fields_benchmark_dataset]))

    @benchmark
    def bench():
        async def _bench():
            await BenchmarkFewFields.filter(level__in=random.sample(levels, 5)).limit(5)

        loop.run_until_complete(_bench())
