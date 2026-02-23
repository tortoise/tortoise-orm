"""Benchmarks for model hydration and query building at scale.

Each benchmark reads/builds many objects per iteration so that Python-level
overhead (hydration, cloning, value conversion) is amplified relative to
per-query DB I/O.
"""

import asyncio
import random

from tests.testmodels import Author, BenchmarkFewFields, BenchmarkManyFields, Book


def test_hydrate_100_rows_few_fields(benchmark, few_fields_benchmark_dataset):
    """Read 100 rows of a small model — _init_from_db called 100x."""
    loop = asyncio.get_event_loop()

    @benchmark
    def bench():
        async def _bench():
            await BenchmarkFewFields.all()

        loop.run_until_complete(_bench())


def test_hydrate_100_rows_many_fields(benchmark, many_fields_benchmark_dataset):
    """Read 100 rows of a large (30+ field) model — _init_from_db called 100x."""
    loop = asyncio.get_event_loop()

    @benchmark
    def bench():
        async def _bench():
            await BenchmarkManyFields.all()

        loop.run_until_complete(_bench())


def test_values_list_100_rows(benchmark, few_fields_benchmark_dataset):
    """values_list() over 100 rows — resolve_to_python_value called per field per row."""
    loop = asyncio.get_event_loop()

    @benchmark
    def bench():
        async def _bench():
            await BenchmarkFewFields.all().values_list("id", "level", "text", flat=False)

        loop.run_until_complete(_bench())


def test_values_100_rows_many_fields(benchmark, many_fields_benchmark_dataset):
    """values() over 100 rows with 8 selected fields."""
    loop = asyncio.get_event_loop()

    @benchmark
    def bench():
        async def _bench():
            await BenchmarkManyFields.all().values(
                "id",
                "level",
                "text",
                "col_float1",
                "col_int1",
                "col_char1",
                "col_decimal1",
                "col_json1",
            )

        loop.run_until_complete(_bench())


def test_select_related_100_rows(benchmark, db):
    """select_related with FK over 100 rows — column split cache + hydration."""
    loop = asyncio.get_event_loop()

    async def _setup():
        await Author.bulk_create([Author(name=f"Author {i}") for i in range(10)])
        author_ids = [a.id for a in await Author.all()]
        await Book.bulk_create(
            [
                Book(
                    name=f"Book {i}",
                    author_id=random.choice(author_ids),  # nosec
                    rating=round(random.uniform(1.0, 5.0), 2),  # nosec
                )
                for i in range(100)
            ]
        )

    loop.run_until_complete(_setup())

    @benchmark
    def bench():
        async def _bench():
            await Book.all().select_related("author")

        loop.run_until_complete(_bench())


def test_chained_filters_10(benchmark, few_fields_benchmark_dataset):
    """Build and execute 10 chained filter queries — _clone() called 20x."""
    loop = asyncio.get_event_loop()

    @benchmark
    def bench():
        async def _bench():
            for i in range(10):
                await BenchmarkFewFields.filter(level=i).filter(text=f"item_{i}")

        loop.run_until_complete(_bench())


def test_constructor_100_many_defaults(benchmark, db):
    """Construct 100 model instances with many defaults — deepcopy skip path."""

    @benchmark
    def bench():
        for _ in range(100):
            BenchmarkManyFields(level=1, text="test")
