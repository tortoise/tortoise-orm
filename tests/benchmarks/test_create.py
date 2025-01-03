import asyncio
import random

from tests.testmodels import BenchmarkFewFields, BenchmarkManyFields


def test_create_few_fields(benchmark):
    loop = asyncio.get_event_loop()

    @benchmark
    def bench():
        async def _bench():
            level = random.randint(0, 100)  # nosec
            await BenchmarkFewFields.create(level=level, text="test")

        loop.run_until_complete(_bench())


def test_create_many_fields(benchmark, gen_many_fields_data):
    loop = asyncio.get_event_loop()

    @benchmark
    def bench():
        async def _bench():
            await BenchmarkManyFields.create(**gen_many_fields_data())

        loop.run_until_complete(_bench())
