import pytest

from tests.testmodels import Author, Book, DefaultOrdered, SourceFieldPk, Tournament
from tortoise.contrib import test
from tortoise.contrib.test.condition import NotIn
from tortoise.exceptions import OperationalError
from tortoise.functions import Count

# ---------------------------------------------------------------------------
# Basic DISTINCT (all databases)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_distinct_no_args(db):
    await Tournament.create(name="1", desc="a")
    await Tournament.create(name="1", desc="b")
    tournaments = await Tournament.all().distinct()
    assert len(tournaments) == 2


# ---------------------------------------------------------------------------
# DISTINCT ON (PostgreSQL only)
# ---------------------------------------------------------------------------


@test.requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_distinct_on_single_field(db):
    tournament_1 = await Tournament.create(name="1", desc="1")
    await Tournament.create(name="1", desc="2")
    await Tournament.create(name="1", desc="3")

    tournaments = await Tournament.all().distinct("name")
    assert tournaments == [tournament_1]


@test.requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_distinct_on_single_field_with_order_by(db):
    await Tournament.create(name="1", desc="1")
    await Tournament.create(name="1", desc="2")
    tournament_3 = await Tournament.create(name="1", desc="3")

    tournaments = await Tournament.all().distinct("name").order_by("name", "-desc")
    assert tournaments == [tournament_3]


@test.requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_distinct_on_multiple_fields(db):
    tournament_1 = await Tournament.create(name="1", desc="a")
    await Tournament.create(name="1", desc="a")
    tournament_3 = await Tournament.create(name="2", desc="b")

    tournaments = await Tournament.all().distinct("name", "desc").order_by("name", "desc")
    assert tournaments == [tournament_1, tournament_3]


@test.requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_distinct_on_values_list_single_field(db):
    """values_list selects one field, same as DISTINCT ON field."""
    await Tournament.create(name="1", desc="a")
    await Tournament.create(name="1", desc="b")
    await Tournament.create(name="2", desc="c")

    tournaments = await Tournament.all().distinct("name").values_list("name", flat=True)
    assert tournaments == ["1", "2"]


@test.requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_distinct_on_values_list_multiple_fields(db):
    await Tournament.create(name="1", desc="a")
    await Tournament.create(name="1", desc="b")
    await Tournament.create(name="2", desc="c")

    tournaments = await Tournament.all().distinct("name").values_list("name", "desc")
    assert tournaments == [("1", "a"), ("2", "c")]


@test.requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_distinct_on_values_list_extra_fields(db):
    await Tournament.create(name="1", desc="a")
    await Tournament.create(name="1", desc="b")
    await Tournament.create(name="2", desc="c")

    tournaments = await Tournament.all().distinct("name").values_list("desc", flat=True)
    assert tournaments == ["a", "c"]


@test.requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_distinct_on_values_list_extra_field_respects_order_by(db):
    await Tournament.create(name="1", desc="a")
    await Tournament.create(name="1", desc="b")
    await Tournament.create(name="2", desc="c")

    tournaments = (
        await Tournament.all()
        .distinct("name")
        .order_by("name", "-desc")
        .values_list("desc", flat=True)
    )
    assert tournaments == ["b", "c"]


@test.requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_distinct_on_values_single_field(db):
    await Tournament.create(name="1", desc="a")
    await Tournament.create(name="1", desc="b")
    await Tournament.create(name="2", desc="c")

    tournaments = await Tournament.all().distinct("name").values("name")
    assert tournaments == [{"name": "1"}, {"name": "2"}]


@test.requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_distinct_on_values_multiple_fields(db):
    await Tournament.create(name="1", desc="a")
    await Tournament.create(name="1", desc="b")
    await Tournament.create(name="2", desc="c")

    tournaments = await Tournament.all().distinct("name").values("name", "desc")
    assert tournaments == [{"name": "1", "desc": "a"}, {"name": "2", "desc": "c"}]


@test.requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_distinct_on_values_extra_fields(db):
    await Tournament.create(name="1", desc="a")
    await Tournament.create(name="1", desc="b")
    await Tournament.create(name="2", desc="c")

    tournaments = await Tournament.all().distinct("name").values("desc")
    assert tournaments == [{"desc": "a"}, {"desc": "c"}]


@test.requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_distinct_on_values_extra_field_respects_order_by(db):
    await Tournament.create(name="1", desc="a")
    await Tournament.create(name="1", desc="b")
    await Tournament.create(name="2", desc="c")

    tournaments = await Tournament.all().distinct("name").order_by("name", "-desc").values("desc")
    assert tournaments == [{"desc": "b"}, {"desc": "c"}]


@test.requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_distinct_on_only_same_field(db):
    await Tournament.create(name="1", desc="a")
    await Tournament.create(name="1", desc="b")
    await Tournament.create(name="2", desc="c")

    tournaments = await Tournament.all().distinct("name").only("name")
    assert [t.name for t in tournaments] == ["1", "2"]


@test.requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_distinct_on_only_extra_field(db):
    await Tournament.create(name="1", desc="a")
    await Tournament.create(name="1", desc="b")
    await Tournament.create(name="2", desc="c")

    tournaments = await Tournament.all().distinct("name").only("name", "desc")
    assert [(t.name, t.desc) for t in tournaments] == [("1", "a"), ("2", "c")]


@test.requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_distinct_on_only_with_order_by(db):
    await Tournament.create(name="1", desc="a")
    await Tournament.create(name="1", desc="b")
    await Tournament.create(name="2", desc="c")

    tournaments = (
        await Tournament.all().distinct("name").order_by("name", "-desc").only("name", "desc")
    )
    assert [(t.name, t.desc) for t in tournaments] == [("1", "b"), ("2", "c")]


@test.requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_distinct_on_filter_by_model(db):
    tournament_1 = await Tournament.create(name="1", desc="a")
    await Tournament.create(name="1", desc="b")
    tournament_2 = await Tournament.create(name="2", desc="c")
    tournaments = await Tournament.filter(name__in=["1", "2"]).distinct("name")
    assert [tournament_1, tournament_2] == tournaments


@test.requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_distinct_on_source_field(db):
    await SourceFieldPk.create(name="1")
    await SourceFieldPk.create(name="2")
    await SourceFieldPk.all().distinct("id")


@test.requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_distinct_on_annotate_by_model(db):
    await Tournament.create(name="1", desc="a")
    await Tournament.create(name="1", desc="b")
    await Tournament.create(name="2", desc="c")
    tournaments = (
        await Tournament.annotate(count_name=Count("name")).distinct("name").order_by("name")
    )
    assert [1, 1] == [tournaments[0].count_name, tournaments[0].count_name]


@test.requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_distinct_on_default_ordered(db):
    await DefaultOrdered.create(one="1", second=1)
    await DefaultOrdered.create(one="2", second=2)
    await DefaultOrdered.all().distinct("one")


@test.requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_distinct_on_by_relation(db):
    author_1 = await Author.create(name="1")
    author_2 = await Author.create(name="1")
    await Book.create(name="1", rating=1, subject="1", author=author_1)
    await Book.create(name="2", rating=2, subject="2", author=author_2)
    books = await Book.all().distinct("author__name")
    assert len(books) == 1


# ---------------------------------------------------------------------------
# DISTINCT ON validation errors
# ---------------------------------------------------------------------------


@test.requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_distinct_on_invalid_order_by(db):
    await Tournament.create(name="1")
    with pytest.raises(OperationalError):
        await Tournament.all().distinct("name").order_by("desc")


@test.requireCapability(dialect=NotIn("postgres"))
@pytest.mark.asyncio
async def test_distinct_on_not_supported_outside_postgres(db):
    with pytest.raises(OperationalError):
        await Tournament.all().distinct("name")


@test.requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_distinct_on_invalid_default_ordered(db):
    await DefaultOrdered.create(one="1", second=1)
    await DefaultOrdered.create(one="2", second=2)
    with pytest.raises(OperationalError):
        await DefaultOrdered.all().distinct("second")
