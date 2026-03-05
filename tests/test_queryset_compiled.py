from typing import Any

import pytest

from tests.testmodels import Author, Book, CharPkModel
from tortoise.exceptions import ParamsError, ValidationError
from tortoise.expressions import Q, Subquery
from tortoise.parameter import Parameter


def test_prepared_queryset_query_always_same(db):
    cache_key = "test_prepared_queryset_always_same"
    prepared = Author.filter(id=Parameter("some_param")).compile(cache_key)
    assert Author.all().compile(cache_key).query is prepared.query


@pytest.mark.asyncio
async def test_gte_filter(db):
    author2 = await Author.create(name="2")
    author3 = await Author.create(name="3")

    expected = await Author.filter(id__gte=author2.pk).order_by("id")

    prepared = Author.filter(id__gte=Parameter("idgte")).order_by("id").compile("test_gte_filter")
    print(prepared.sql(idgte=author2.pk))
    actual = await prepared.execute(idgte=author2.pk)
    assert len(actual) == 2
    assert actual[0].pk == author2.pk
    assert actual[1].pk == author3.pk
    assert expected == actual


@pytest.mark.asyncio
async def test_string_param(db):
    await Author.create(name="1")
    author2 = await Author.create(name="2")
    await Author.create(name="3")

    expected = await Author.filter(name=author2.name)

    prepared = Author.filter(name=Parameter("name")).compile("test_string_param")
    actual = await prepared.execute(name=author2.name)
    assert len(actual) == 1
    assert actual[0].pk == author2.pk
    assert expected == actual


@pytest.mark.asyncio
async def test_startswith_filter(db):
    author1 = await Author.create(name="test")
    author2 = await Author.create(name="testqwe")
    author3 = await Author.create(name="qwetest")

    prepared = Author.filter(name__startswith=Parameter("name")).compile("test_startswith_filter")

    for test_name in (author2.pk, author1.name, author3.name, "asd"):
        expected = await Author.filter(name__startswith=test_name)
        actual = await prepared.execute(name=test_name)
        assert expected == actual


@pytest.mark.asyncio
async def test_in_filter(db):
    author1 = await Author.create(name="test")
    author2 = await Author.create(name="testqwe")
    author3 = await Author.create(name="qwetest")

    prepared = Author.filter(id__in=Parameter("ids")).compile("test_in_filter")

    for test_ids in ([author2.pk, author1.pk], [author3.pk, author3.pk * 2, author3.pk * 10]):
        expected = await Author.filter(id__in=test_ids)
        actual = await prepared.execute(ids=test_ids)
        assert expected == actual


@pytest.mark.asyncio
async def test_subqueries(db):
    author1 = await Author.create(name="1")
    author2 = await Author.create(name="2")
    author3 = await Author.create(name="3")

    prepared = Author.filter(
        id__in=Subquery(Author.filter(Q(id=Parameter("id1")) | Q(id=Parameter("id2"))).values("id"))
    ).compile("test_subqueries")

    for id1, id2 in (
        (author2.pk, author1.pk),
        (author3.pk, author3.pk * 2),
    ):
        expected = await Author.filter(
            id__in=Subquery(Author.filter(Q(id=id1) | Q(id=id2)).values("id"))
        )
        actual = await prepared.execute(id1=id1, id2=id2)
        assert expected == actual


@pytest.mark.asyncio
async def test_subqueries_in_filter(db):
    author1 = await Author.create(name="1")
    author2 = await Author.create(name="2")
    author3 = await Author.create(name="3")

    prepared = Author.filter(
        id__in=Subquery(Author.filter(id__in=Parameter("ids")).values("id"))
    ).compile("test_subqueries_in_filter")

    for test_ids in ([author2.pk, author1.pk], [author3.pk, author3.pk * 2, author3.pk * 10]):
        expected = await Author.filter(id__in=Subquery(Author.filter(id__in=test_ids).values("id")))
        actual = await prepared.execute(ids=test_ids)
        assert expected == actual


@pytest.mark.asyncio
async def test_update(db):
    author1 = await Author.create(name="1")
    author2 = await Author.create(name="2")

    original_name1 = author1.name
    original_name2 = author2.name
    new_name1 = f"{author1.name}_test"

    prepared = (
        Author.filter(id=Parameter("search_id"))
        .update(name=Parameter("replace_name"))
        .compile("test_update")
    )

    await prepared.execute(search_id=author1.pk, replace_name=new_name1)
    await author1.refresh_from_db(["name"])
    await author2.refresh_from_db(["name"])
    assert author1.name == new_name1
    assert author2.name == original_name2

    await prepared.execute(search_id=author1.pk, replace_name=original_name1)
    await author1.refresh_from_db(["name"])
    assert author1.name == original_name1


@pytest.mark.asyncio
async def test_delete(db):
    author1 = await Author.create(name="1")
    author2 = await Author.create(name="2")
    author3 = await Author.create(name="3")

    prepared = (
        Author.filter(
            id__in=Parameter("ids"),
        )
        .delete()
        .compile("test_delete")
    )

    affected = await prepared.execute(ids=[author1.pk])
    assert affected == 1
    assert await Author.all().count() == 2
    existing = await Author.all().values_list("id", flat=True)
    assert set(existing) == {author2.pk, author3.pk}


@pytest.mark.asyncio
async def test_exists(db):
    author = await Author.create(name="1")

    prepared = (
        Author.filter(
            id__in=Parameter("ids"),
        )
        .exists()
        .compile("test_exists")
    )

    assert await prepared.execute(ids=[author.pk])
    assert not await prepared.execute(ids=[author.pk * 2])


@pytest.mark.asyncio
async def test_count(db):
    author1 = await Author.create(name="1")
    author2 = await Author.create(name="2")
    author3 = await Author.create(name="3")

    prepared = (
        Author.filter(
            id__gte=Parameter("idgte"),
        )
        .count()
        .compile("test_count")
    )

    assert await prepared.execute(idgte=author1.pk) == 3
    assert await prepared.execute(idgte=author2.pk) == 2
    assert await prepared.execute(idgte=author3.pk) == 1
    assert await prepared.execute(idgte=author3.pk * 2) == 0


@pytest.mark.asyncio
async def test_parameter_in_limit(db):
    await Author.bulk_create(
        [
            Author(name="1"),
            Author(name="2"),
            Author(name="3"),
        ]
    )

    prepared = (
        Author.all().limit(Parameter("lim")).order_by("id").compile("test_parameter_in_limit")
    )

    assert len(await prepared.execute(lim=1)) == 1
    assert len(await prepared.execute(lim=2)) == 2
    assert len(await prepared.execute(lim=3)) == 3
    assert len(await prepared.execute(lim=4)) == 3

    with pytest.raises(ParamsError):
        await prepared.execute(lim=-1)


@pytest.mark.asyncio
async def test_parameter_in_offset(db):
    await Author.bulk_create(
        [
            Author(name="1"),
            Author(name="2"),
            Author(name="3"),
        ]
    )

    prepared = (
        Author.all().offset(Parameter("off")).order_by("id").compile("test_parameter_in_offset")
    )

    assert len(await prepared.execute(off=1)) == 2
    assert len(await prepared.execute(off=2)) == 1
    assert len(await prepared.execute(off=3)) == 0
    assert len(await prepared.execute(off=4)) == 0

    with pytest.raises(ParamsError):
        await prepared.execute(off=-1)


@pytest.mark.asyncio
async def test_values(db):
    author = await Author.create(name="1")

    prepared = (
        Author.filter(
            id=Parameter("id"),
        )
        .values()
        .compile("test_values")
    )

    assert await prepared.execute(id=author.pk) == [{"id": author.pk, "name": author.name}]
    assert await prepared.execute(id=author.pk * 2) == []


@pytest.mark.asyncio
async def test_values_list_all_fields(db):
    author = await Author.create(name="1")

    prepared_all = (
        Author.filter(
            id=Parameter("id"),
        )
        .values_list()
        .compile("test_values_list_all_fields")
    )
    assert await prepared_all.execute(id=author.pk) == [(author.pk, author.name)]
    assert await prepared_all.execute(id=author.pk * 2) == []


@pytest.mark.asyncio
async def test_values_list_only_id_field(db):
    author = await Author.create(name="1")

    prepared_ids = (
        Author.filter(
            id=Parameter("id"),
        )
        .values_list("id")
        .compile("test_values_list_only_id_field")
    )
    assert await prepared_ids.execute(id=author.pk) == [(author.pk,)]
    assert await prepared_ids.execute(id=author.pk * 2) == []


@pytest.mark.asyncio
async def test_values_list_only_id_field_flat(db):
    author = await Author.create(name="1")

    prepared_ids_flat = (
        Author.filter(
            id=Parameter("id"),
        )
        .values_list("id", flat=True)
        .compile("test_values_list_only_id_field_flat")
    )
    assert await prepared_ids_flat.execute(id=author.pk) == [author.pk]
    assert await prepared_ids_flat.execute(id=author.pk * 2) == []


@pytest.mark.asyncio
async def test_update_fk(db):
    author1 = await Author.create(name="1")
    author2 = await Author.create(name="2")

    book = await Book.create(name="test", author=author1, rating=5)

    prepared = (
        Book.filter(id=Parameter("search_id"))
        .update(author=Parameter("replace_author"))
        .compile("test_update_fk")
    )

    await prepared.execute(search_id=book.pk, replace_author=author2)
    book = await Book.get(id=book.pk).select_related("author")
    # await book.refresh_from_db(["author_id"])
    assert book.author == author2

    await prepared.execute(search_id=book.pk, replace_author=author1)
    book = await Book.get(id=book.pk).select_related("author")
    # await book.refresh_from_db(["author_id"])
    assert book.author == author1


@pytest.mark.asyncio
async def test_update_pk_invalid_obj(db):
    author = await Author.create(name="1")
    book = await Book.create(name="test", author=author, rating=5)

    prepared = (
        Book.filter(id=Parameter("search_id"))
        .update(author=Parameter("replace_author"))
        .compile("test_update_pk_invalid_obj")
    )

    with pytest.raises(ValidationError):
        await prepared.execute(search_id=book.pk, replace_author="not an Author object")


def test_remove_prepared_queryset_from_cache(db):
    cache_key = "test_remove_query_from_cache"
    prepared = Author.filter(id=Parameter("some_param")).compile(cache_key)
    assert Author.all().compile(cache_key).query is prepared.query
    Author.remove_compiled_query(cache_key)
    assert Author.all().compile(cache_key).query is not prepared.query


@pytest.mark.parametrize(
    (
        "filter_kwargs",
        "cache_key_suffix",
    ),
    [
        ({"id": "123"}, "1"),
        ({"id__gte": "321"}, "2"),
        ({"id__in": ["321", 123, 987]}, "3"),
    ],
)
def test_prepared_query_get_sql(db, filter_kwargs: dict[str, Any], cache_key_suffix: str):
    expected_sql = CharPkModel.all().filter(**filter_kwargs).limit(10).offset(0).sql()
    actual_sql = (
        CharPkModel.all()
        .filter(**{key: Parameter(key) for key in filter_kwargs})
        .limit(10)
        .offset(0)
        .compile(f"test_prepared_query_get_sql-{cache_key_suffix}")
        .sql(**filter_kwargs)
    )

    assert expected_sql == actual_sql


def test_compiled_query_auto_cache_size(db):
    compiled = Author.filter(id=Parameter("id")).compile()
    # Trigger sql generation
    compiled.sql(id=1)
    assert compiled._sql_cache.maxsize == compiled.DEFAULT_CACHE_SIZE_SIMPLE

    compiled = Author.filter(
        id__in=Subquery(Author.filter(Q(id=Parameter("id1")) | Q(id=Parameter("id2"))))
    ).compile()
    compiled.sql(id1=1, id2=2)
    assert compiled._sql_cache.maxsize == compiled.DEFAULT_CACHE_SIZE_SIMPLE

    compiled = Author.filter(id__in=Parameter("ids")).compile()
    compiled.sql(ids=[1])
    assert compiled._sql_cache.maxsize == compiled.DEFAULT_CACHE_SIZE_COLLECTIONS
