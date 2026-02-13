import random
import time

from tortoise import fields, run_async
from tortoise.contrib.test import init_memory_sqlite
from tortoise.expressions import Q
from tortoise.functions import Min, Max
from tortoise.models import Model
from tortoise.parameter import Parameter


CHECK_ACTUAL = True


class SomeModel(Model):
    id: int = fields.BigIntField(pk=True)
    name: str = fields.TextField()


async def t0_sanity_check(some1: SomeModel, some2: SomeModel, some3: SomeModel) -> None:
    idk = await SomeModel.filter(id=some2.id)
    print(idk)


async def t1_simple_gte(some1: SomeModel, some2: SomeModel, some3: SomeModel) -> None:
    query = SomeModel.filter(id__gte=Parameter("idk"))
    prepared = query.prepare()
    actual = await prepared.execute(idk=some2.id)
    print(actual)

    if CHECK_ACTUAL:
        expected = await SomeModel.filter(id__gte=some2.id)
        print(expected)
        print(actual == expected)


async def t2_simple_string_param(some1: SomeModel, some2: SomeModel, some3: SomeModel) -> None:
    query = SomeModel.filter(name=Parameter("idk"))
    prepared = query.prepare()
    actual1 = await prepared.execute(idk=some2.id)
    print(actual1)
    actual2 = await prepared.execute(idk=some2.name)
    print(actual2)

    if CHECK_ACTUAL:
        expected1 = await SomeModel.filter(name=some2.id)
        expected2 = await SomeModel.filter(name=some2.name)
        print(expected1)
        print(expected2)
        print(actual1 == expected1)
        print(actual2 == expected2)


async def t3_startswith(some1: SomeModel, some2: SomeModel, some3: SomeModel) -> None:
    query = SomeModel.filter(name__startswith=Parameter("idk"))
    prepared = query.prepare()
    actual1 = await prepared.execute(idk=some2.id)
    print(actual1)
    actual2 = await prepared.execute(idk=some2.name)
    print(actual2)
    actual3 = await prepared.execute(idk="asd")
    print(actual3)
    actual4 = await prepared.execute(idk="qwe")
    print(actual4)

    if CHECK_ACTUAL:
        expected1 = await SomeModel.filter(name__startswith=some2.id)
        expected2 = await SomeModel.filter(name__startswith=some2.name)
        expected3 = await SomeModel.filter(name__startswith="asd")
        expected4 = await SomeModel.filter(name__startswith="qwe")
        print(expected1)
        print(expected2)
        print(expected3)
        print(expected4)
        print(actual1 == expected1)
        print(actual2 == expected2)
        print(actual3 == expected3)
        print(actual4 == expected4)


async def t4_in(some1: SomeModel, some2: SomeModel, some3: SomeModel) -> None:
    query = SomeModel.filter(id__in=Parameter("idk"))
    prepared = query.prepare()
    actual1 = await prepared.execute(idk=[some2.id, some1.id])
    print(actual1)
    actual2 = await prepared.execute(idk=[some3.id, some3.id * 2, some3.id * 10])
    print(actual2)

    if CHECK_ACTUAL:
        expected1 = await SomeModel.filter(id__in=[some2.id, some1.id])
        expected2 = await SomeModel.filter(id__in=[some3.id, some3.id * 2, some3.id * 10])
        print(expected1)
        print(expected2)
        print(actual1 == expected1)
        print(actual2 == expected2)


async def t5_compare_prepared_non_prepared(*_) -> None:
    ITERS = 1000

    prefix = f"{time.time()}-"
    await SomeModel.bulk_create([
        SomeModel(name=f"{prefix}{num}")
        for num in range(1000)
    ])

    min_id, max_id = await SomeModel.filter(name__startswith=prefix).annotate(max_id=Max("id"), min_id=Min("id")).first().values_list("min_id", "max_id")
    random_id = random.randint(min_id, max_id)

    random_ids = await SomeModel.filter(name__startswith=prefix).values_list("id", flat=True)
    random.shuffle(random_ids)
    random_ids = random_ids[:2]

    start_time = time.perf_counter()
    for _ in range(ITERS):
        await SomeModel.filter(Q(id__lte=random_id * 2, id__in=random_ids, join_type=Q.OR), id__gte=random_id)
    end_time = time.perf_counter()
    non_prepared_millis = (end_time - start_time) * 1000
    print(f"Non-prepared: {non_prepared_millis:.2f}ms")

    start_time = time.perf_counter()
    query = SomeModel.filter(Q(id__lte=Parameter("id_lte"), id__in=Parameter("id_in"), join_type=Q.OR), id__gte=Parameter("id_gte")).prepare()
    for _ in range(ITERS):
        await query.execute(id_lte=random_id * 2, id_gte=random_id, id_in=random_ids)
    end_time = time.perf_counter()
    prepared_millis = (end_time - start_time) * 1000
    print(f"Prepared: {prepared_millis:.2f}ms")

    if non_prepared_millis > prepared_millis:
        ratio = non_prepared_millis / prepared_millis
        result = "faster"
    else:
        ratio = prepared_millis / non_prepared_millis
        result = "slower"

    print(f"Prepared is {(ratio - 1) * 100:.2f}% {result} than non-prepared")

    await SomeModel.filter(name__startswith=prefix).delete()


TESTS = [
    # t0_sanity_check,
    # t1_simple_gte,
    # t2_simple_string_param,
    # t3_startswith,
    # t4_in,
    t5_compare_prepared_non_prepared,
]


@init_memory_sqlite
async def run() -> None:
    some1 = await SomeModel.create(name="asdqwe")
    some2 = await SomeModel.create(name="asdqweasd")
    some3 = await SomeModel.create(name="asdqweasd123")

    for test_func in TESTS:
        print(f"Running {test_func.__name__} ...")
        await test_func(some1, some2, some3)
        print("=" * 32)


if __name__ == "__main__":
    run_async(run())