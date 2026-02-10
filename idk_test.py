from tortoise import fields, run_async
from tortoise.contrib.test import init_memory_sqlite
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


TESTS = [
    # t0_sanity_check,
    # t1_simple_gte,
    # t2_simple_string_param,
    # t3_startswith,
    t4_in,
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