import random
import time

from tortoise import fields, run_async
from tortoise.contrib.test import init_memory_sqlite
from tortoise.expressions import Q, Subquery
from tortoise.functions import Min, Max
from tortoise.models import Model
from tortoise.parameter import Parameter


CHECK_ACTUAL = True


class SomeModel(Model):
    id: int = fields.BigIntField(pk=True)
    name: str = fields.TextField()


class SomeForeignKeyModel(Model):
    id: int = fields.BigIntField(pk=True)
    info: str = fields.CharField(max_length=128, default="")
    some: SomeModel = fields.ForeignKeyField("models.SomeModel")


async def t0_sanity_check(some1: SomeModel, some2: SomeModel, some3: SomeModel) -> None:
    idk = await SomeModel.filter(id=some2.id)
    print(idk)

    cache_key = "_some_query"
    prepared = SomeModel.prepare_sql(cache_key).filter(id=Parameter("idk")).prepared()
    assert SomeModel.prepare_sql(cache_key) is prepared
    try:
        prepared.filter(id=1)
    except ValueError:
        ...
    else:
        raise RuntimeError("PreparedQuerySet.filter on prepared query should raise")


async def t1_simple_gte(some1: SomeModel, some2: SomeModel, some3: SomeModel) -> None:
    prepared = SomeModel.prepare_sql("some_query1").filter(id__gte=Parameter("idk")).prepared()
    actual = await prepared.execute(idk=some2.id)
    print(actual)

    if CHECK_ACTUAL:
        expected = await SomeModel.filter(id__gte=some2.id)
        print(expected)
        print(actual == expected)


async def t2_simple_string_param(some1: SomeModel, some2: SomeModel, some3: SomeModel) -> None:
    prepared = SomeModel.prepare_sql("some_query2").filter(name=Parameter("idk")).prepared()
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
    prepared = SomeModel.prepare_sql("some_query3").filter(name__startswith=Parameter("idk")).prepared()
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
    prepared = SomeModel.prepare_sql("some_query4").filter(id__in=Parameter("idk")).prepared()
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
    query = SomeModel.prepare_sql("some_query5").filter(Q(id__lte=Parameter("id_lte"), id__in=Parameter("id_in"), join_type=Q.OR), id__gte=Parameter("id_gte")).prepared()
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


async def t6_subqueries(some1: SomeModel, some2: SomeModel, some3: SomeModel) -> None:
    prepared = SomeModel.prepare_sql("some_query6").filter(id__in=Subquery(SomeModel.filter(Q(id=Parameter("idk1")) | Q(id=Parameter("idk2"))).values("id"))).prepared()
    actual1 = await prepared.execute(idk1=some2.id, idk2=some1.id)
    print(actual1)
    actual2 = await prepared.execute(idk1=some3.id, idk2=some3.id * 2)
    print(actual2)

    if CHECK_ACTUAL:
        expected1 = await SomeModel.filter(id__in=Subquery(SomeModel.filter(Q(id=some2.id) | Q(id=some1.id)).values("id")))
        expected2 = await SomeModel.filter(id__in=Subquery(SomeModel.filter(Q(id=some3.id) | Q(id=some3.id * 2)).values("id")))
        print(expected1)
        print(expected2)
        print(actual1 == expected1)
        print(actual2 == expected2)


async def t7_subqueries_in(some1: SomeModel, some2: SomeModel, some3: SomeModel) -> None:
    prepared = SomeModel.prepare_sql("some_query7").filter(id__in=Subquery(SomeModel.filter(id__in=Parameter("idk")).values("id"))).prepared()
    actual1 = await prepared.execute(idk=[some2.id, some1.id])
    print(actual1)
    actual2 = await prepared.execute(idk=[some3.id, some3.id * 2, some3.id * 10])
    print(actual2)

    if CHECK_ACTUAL:
        expected1 = await SomeModel.filter(id__in=Subquery(SomeModel.filter(id__in=[some2.id, some1.id]).values("id")))
        expected2 = await SomeModel.filter(id__in=Subquery(SomeModel.filter(id__in=[some3.id, some3.id * 2, some3.id * 10]).values("id")))
        print(expected1)
        print(expected2)
        print(actual1 == expected1)
        print(actual2 == expected2)


async def t8_update(some1: SomeModel, some2: SomeModel, some3: SomeModel) -> None:
    original_name = some1.name

    prepared = SomeModel.prepare_sql("some_query8").filter(id=Parameter("search_id")).update(name=Parameter("replace_name")).prepared()
    await prepared.execute(search_id=some1.id, replace_name=some1.name + "_test")
    await some1.refresh_from_db(["name"])
    print(f"{original_name!r} -> {some1.name!r}")
    await prepared.execute(search_id=some1.id, replace_name=original_name)
    await some1.refresh_from_db(["name"])
    print(f"back to {original_name!r}: {some1.name!r}")

    if CHECK_ACTUAL:
        await SomeModel.filter(id=some1.id).update(name=some1.name + "_test")
        await some1.refresh_from_db(["name"])
        print(f"{original_name!r} -> {some1.name!r}")
        await SomeModel.filter(id=some1.id).update(name=original_name)
        await some1.refresh_from_db(["name"])
        print(f"back to {original_name!r}: {some1.name!r}")


TESTS = [
    t0_sanity_check,
    t1_simple_gte,
    t2_simple_string_param,
    t3_startswith,
    t4_in,
    t5_compare_prepared_non_prepared,
    t6_subqueries,
    t7_subqueries_in,
    t8_update,
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