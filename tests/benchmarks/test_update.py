import asyncio
import random

from tests.testmodels import BenchmarkFewFields, BenchmarkManyFields


def test_update_few_fields_with_save(benchmark, few_fields_benchmark_dataset):
    loop = asyncio.get_event_loop()

    @benchmark
    def bench():
        async def _bench():
            instance = random.choice(few_fields_benchmark_dataset)  # nosec
            instance.level = random.randint(0, 100)  # nosec
            instance.text = "updated " + str(random.randint(0, 100))  # nosec
            await instance.save()

        loop.run_until_complete(_bench())


def test_update_many_fields_with_save(
    benchmark, many_fields_benchmark_dataset, gen_many_fields_data
):
    loop = asyncio.get_event_loop()

    @benchmark
    def bench():
        async def _bench():
            instance = random.choice(many_fields_benchmark_dataset)  # nosec
            rand_val = random.randint(0, 100)  # nosec
            instance.col_float1 = random.uniform(0, 100)  # nosec
            instance.col_smallint1 = rand_val
            instance.col_int1 = rand_val
            instance.col_bigint1 = rand_val
            instance.col_char1 = "updated " + str(rand_val)
            instance.col_text1 = "updated " + str(rand_val)
            await instance.save()

        loop.run_until_complete(_bench())


def test_update_few_fields_with_update(benchmark, few_fields_benchmark_dataset):
    loop = asyncio.get_event_loop()

    @benchmark
    def bench():
        async def _bench():
            instance = random.choice(few_fields_benchmark_dataset)  # nosec
            await BenchmarkFewFields.filter(id=instance.id).update(
                level=random.randint(0, 100),  # nosec
                text="updated " + str(random.randint(0, 100)),  # nosec
            )

        loop.run_until_complete(_bench())


def test_update_many_fields_with_update(
    benchmark, many_fields_benchmark_dataset, gen_many_fields_data
):
    loop = asyncio.get_event_loop()

    @benchmark
    def bench():
        async def _bench():
            instance = random.choice(many_fields_benchmark_dataset)  # nosec
            rand_val = random.randint(0, 100)  # nosec
            await BenchmarkManyFields.filter(id=instance.id).update(
                col_float1=random.uniform(0, 100),  # nosec
                col_smallint1=rand_val,
                col_int1=rand_val,
                col_bigint1=rand_val,
                col_char1="updated " + str(rand_val),
                col_text1="updated " + str(rand_val),
            )

        loop.run_until_complete(_bench())
