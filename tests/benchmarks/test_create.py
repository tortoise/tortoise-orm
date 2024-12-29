import asyncio
from decimal import Decimal
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


def test_create_many_fields(benchmark):
    loop = asyncio.get_event_loop()

    @benchmark
    def bench():
        async def _bench():
            await BenchmarkManyFields.create(
                level=random.randint(0, 100),  # nosec
                text="test",
                col_float1=2.2,
                col_smallint1=2,
                col_int1=2000000,
                col_bigint1=99999999,
                col_char1="value1",
                col_text1="Moo,Foo,Baa,Waa,Moo,Foo,Baa,Waa,Moo,Foo,Baa,Waa",
                col_decimal1=Decimal("2.2"),
                col_json1={"a": 1, "b": "b", "c": [2], "d": {"e": 3}, "f": True},
                col_float2=0.2,
                col_smallint2=None,
                col_int2=22,
                col_bigint2=None,
                col_char2=None,
                col_text2=None,
                col_decimal2=None,
                col_json2=None,
                col_float3=2.2,
                col_smallint3=2,
                col_int3=2000000,
                col_bigint3=99999999,
                col_char3="value1",
                col_text3="Moo,Foo,Baa,Waa,Moo,Foo,Baa,Waa,Moo,Foo,Baa,Waa",
                col_decimal3=Decimal("2.2"),
                col_json3={"a": 1, "b": 2, "c": [2]},
                col_float4=0.00004,
                col_smallint4=None,
                col_int4=4,
                col_bigint4=99999999000000,
                col_char4="value4",
                col_text4="AAAAAAAA",
                col_decimal4=None,
                col_json4=None,
            )

        loop.run_until_complete(_bench())
