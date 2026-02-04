import pytest

from tests import testmodels
from tortoise.contrib import test


@test.requireCapability(support_for_posix_regex_queries=True)
@pytest.mark.asyncio
async def test_regex_filter(db):
    author = await testmodels.Author.create(name="Johann Wolfgang von Goethe")
    assert set(
        await testmodels.Author.filter(
            name__posix_regex="^Johann [a-zA-Z]+ von Goethe$"
        ).values_list("name", flat=True)
    ) == {author.name}


@test.requireCapability(dialect="postgres", support_for_posix_regex_queries=True)
@pytest.mark.asyncio
async def test_regex_filter_works_with_null_field_postgres(db):
    await testmodels.Tournament.create(name="Test")
    print(testmodels.Tournament.filter(desc__posix_regex="^test$").sql())
    assert (
        set(
            await testmodels.Tournament.filter(desc__posix_regex="^test$").values_list(
                "name", flat=True
            )
        )
        == set()
    )


@test.requireCapability(dialect="sqlite", support_for_posix_regex_queries=True)
@pytest.mark.asyncio
async def test_regex_filter_works_with_null_field_sqlite(db):
    await testmodels.Tournament.create(name="Test")
    print(testmodels.Tournament.filter(desc__posix_regex="^test$").sql())
    assert (
        set(
            await testmodels.Tournament.filter(desc__posix_regex="^test$").values_list(
                "name", flat=True
            )
        )
        == set()
    )


@test.requireCapability(dialect="postgres", support_for_posix_regex_queries=True)
@pytest.mark.asyncio
async def test_case_insensitive_regex_filter_postgres(db):
    author = await testmodels.Author.create(name="Johann Wolfgang von Goethe")
    assert set(
        await testmodels.Author.filter(
            name__iposix_regex="^johann [a-zA-Z]+ Von goethe$"
        ).values_list("name", flat=True)
    ) == {author.name}


@test.requireCapability(dialect="sqlite", support_for_posix_regex_queries=True)
@pytest.mark.asyncio
async def test_case_insensitive_regex_filter_sqlite(db):
    author = await testmodels.Author.create(name="Johann Wolfgang von Goethe")
    assert set(
        await testmodels.Author.filter(
            name__iposix_regex="^johann [a-zA-Z]+ Von goethe$"
        ).values_list("name", flat=True)
    ) == {author.name}
