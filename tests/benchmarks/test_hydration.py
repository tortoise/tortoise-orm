"""Benchmarks for model hydration and query building at scale.

Each benchmark performs many operations per iteration so that Python-level
overhead (hydration, cloning, value conversion) is amplified relative to
per-query DB I/O, producing stable and meaningful numbers.
"""

import asyncio
import random
from decimal import Decimal

from tests.testmodels import Author, BenchmarkFewFields, BenchmarkManyFields, Book


def test_hydrate_1000_rows_few_fields(benchmark, db):
    """Read 1000 rows of a small model — _init_from_db called 1000x."""
    loop = asyncio.get_event_loop()

    async def _setup():
        await BenchmarkFewFields.bulk_create(
            [BenchmarkFewFields(level=i % 100, text=f"item_{i}") for i in range(1000)]
        )

    loop.run_until_complete(_setup())

    @benchmark
    def bench():
        async def _bench():
            await BenchmarkFewFields.all()

        loop.run_until_complete(_bench())


def test_hydrate_1000_rows_many_fields(benchmark, db, gen_many_fields_data):
    """Read 1000 rows of a large (30+ field) model — _init_from_db called 1000x."""
    loop = asyncio.get_event_loop()

    async def _setup():
        await BenchmarkManyFields.bulk_create(
            [BenchmarkManyFields(**gen_many_fields_data()) for _ in range(1000)]
        )

    loop.run_until_complete(_setup())

    @benchmark
    def bench():
        async def _bench():
            await BenchmarkManyFields.all()

        loop.run_until_complete(_bench())


def test_values_list_1000_rows(benchmark, db):
    """values_list() over 1000 rows — resolve_to_python_value called per field per row."""
    loop = asyncio.get_event_loop()

    async def _setup():
        await BenchmarkFewFields.bulk_create(
            [BenchmarkFewFields(level=i % 100, text=f"item_{i}") for i in range(1000)]
        )

    loop.run_until_complete(_setup())

    @benchmark
    def bench():
        async def _bench():
            await BenchmarkFewFields.all().values_list("id", "level", "text", flat=False)

        loop.run_until_complete(_bench())


def test_values_1000_rows_many_fields(benchmark, db, gen_many_fields_data):
    """values() over 1000 rows with 8 selected fields — resolve_to_python_value at scale."""
    loop = asyncio.get_event_loop()

    async def _setup():
        await BenchmarkManyFields.bulk_create(
            [BenchmarkManyFields(**gen_many_fields_data()) for _ in range(1000)]
        )

    loop.run_until_complete(_setup())

    @benchmark
    def bench():
        async def _bench():
            await BenchmarkManyFields.all().values(
                "id", "level", "text", "col_float1",
                "col_int1", "col_char1", "col_decimal1", "col_json1",
            )

        loop.run_until_complete(_bench())


def test_select_related_1000_rows(benchmark, db):
    """select_related with FK over 1000 rows — column split cache + hydration."""
    loop = asyncio.get_event_loop()

    async def _setup():
        authors = await Author.bulk_create(
            [Author(name=f"Author {i}") for i in range(20)]
        )
        author_ids = [a.id for a in await Author.all()]
        await Book.bulk_create(
            [
                Book(
                    name=f"Book {i}",
                    author_id=random.choice(author_ids),  # nosec
                    rating=round(random.uniform(1.0, 5.0), 2),  # nosec
                )
                for i in range(1000)
            ]
        )

    loop.run_until_complete(_setup())

    @benchmark
    def bench():
        async def _bench():
            await Book.all().select_related("author")

        loop.run_until_complete(_bench())


def test_chained_filters_100(benchmark, db):
    """Build and execute 100 chained filter queries — _clone() called 100x."""
    loop = asyncio.get_event_loop()

    async def _setup():
        await BenchmarkFewFields.bulk_create(
            [BenchmarkFewFields(level=i % 100, text=f"item_{i}") for i in range(100)]
        )

    loop.run_until_complete(_setup())

    @benchmark
    def bench():
        async def _bench():
            for i in range(100):
                await BenchmarkFewFields.filter(level=i).filter(text=f"item_{i}")

        loop.run_until_complete(_bench())


def test_constructor_1000_many_defaults(benchmark, db):
    """Construct 1000 model instances with many defaults — deepcopy skip path."""
    loop = asyncio.get_event_loop()

    @benchmark
    def bench():
        for _ in range(1000):
            BenchmarkManyFields(level=1, text="test")
