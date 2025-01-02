import asyncio
import random

from tests.testmodels import BenchmarkFewFields, BenchmarkManyFields


def test_bulk_create_few_fields(benchmark):
    loop = asyncio.get_event_loop()

    data = [
        BenchmarkFewFields(
            level=random.choice([10, 20, 30, 40, 50]), text=f"Insert from C, item {i}"  # nosec
        )
        for i in range(100)
    ]

    @benchmark
    def bench():
        async def _bench():
            await BenchmarkFewFields.bulk_create(data)

        loop.run_until_complete(_bench())


def test_bulk_create_many_fields(benchmark, gen_many_fields_data):
    loop = asyncio.get_event_loop()

    data = [BenchmarkManyFields(**gen_many_fields_data()) for _ in range(100)]

    @benchmark
    def bench():
        async def _bench():
            await BenchmarkManyFields.bulk_create(data)

        loop.run_until_complete(_bench())
