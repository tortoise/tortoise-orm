import asyncio
import random

from tests.testmodels import BenchmarkFewFields, BenchmarkManyFields


def test_get_few_fields(benchmark, few_fields_benchmark_dataset):
    loop = asyncio.get_event_loop()
    minid = min(o.id for o in few_fields_benchmark_dataset)
    maxid = max(o.id for o in few_fields_benchmark_dataset)

    @benchmark
    def bench():
        async def _bench():
            randid = random.randint(minid, maxid)  # nosec
            await BenchmarkFewFields.get(id=randid)

        loop.run_until_complete(_bench())


def test_get_many_fields(benchmark, many_fields_benchmark_dataset):
    loop = asyncio.get_event_loop()
    minid = min(o.id for o in many_fields_benchmark_dataset)
    maxid = max(o.id for o in many_fields_benchmark_dataset)

    @benchmark
    def bench():
        async def _bench():
            randid = random.randint(minid, maxid)  # nosec
            await BenchmarkManyFields.get(id=randid)

        loop.run_until_complete(_bench())
