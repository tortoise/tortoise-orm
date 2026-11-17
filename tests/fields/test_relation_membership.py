from collections.abc import Iterable

import pytest

from tests import testmodels
from tortoise.exceptions import FieldError
from tortoise.expressions import F, Subquery


@pytest.mark.asyncio
@pytest.mark.parametrize("lookup", ["in", "not_in"])
@pytest.mark.parametrize("input_kind", ["models", "iterator", "mixed"])
async def test_foreign_key_membership(db, lookup: str, input_kind: str) -> None:
    tournaments = [await testmodels.Tournament.create(name=str(i)) for i in range(3)]
    relations = [await testmodels.MinRelation.create(tournament=t) for t in tournaments]
    values: Iterable[testmodels.Tournament | int] = tournaments[:2]
    if input_kind == "iterator":
        values = iter(values)
    elif input_kind == "mixed":
        values = [tournaments[0], tournaments[1].pk]

    result = await testmodels.MinRelation.filter(**{f"tournament__{lookup}": values}).order_by("id")
    assert result == (relations[:2] if lookup == "in" else relations[2:])


@pytest.mark.asyncio
@pytest.mark.parametrize("lookup", ["in", "not_in"])
@pytest.mark.parametrize("relation_model", [testmodels.Student, testmodels.Principal])
async def test_membership_uses_referenced_field(
    db, lookup: str, relation_model: type[testmodels.Student] | type[testmodels.Principal]
) -> None:
    first = await testmodels.School.create(name="first", id=101)
    second = await testmodels.School.create(name="second", id=202)
    first_relation = await relation_model.create(name="first", school=first)
    second_relation = await relation_model.create(name="second", school=second)

    result = await relation_model.filter(**{f"school__{lookup}": [first]})
    assert result == [first_relation if lookup == "in" else second_relation]


@pytest.mark.asyncio
@pytest.mark.parametrize("lookup", ["in", "not_in"])
async def test_membership_with_string_primary_keys(db, lookup: str) -> None:
    first = await testmodels.CharPkModel.create(id="first")
    second = await testmodels.CharPkModel.create(id="second")
    first_relation = await testmodels.CharFkRelatedModel.create(model=first)
    second_relation = await testmodels.CharFkRelatedModel.create(model=second)

    result = await testmodels.CharFkRelatedModel.filter(**{f"model__{lookup}": [first]})
    assert result == [first_relation if lookup == "in" else second_relation]


@pytest.mark.asyncio
@pytest.mark.parametrize("lookup", ["in", "not_in"])
async def test_membership_with_renamed_uuid_columns(db, lookup: str) -> None:
    first = await testmodels.UUIDPkSourceModel.create()
    second = await testmodels.UUIDPkSourceModel.create()
    first_relation = await testmodels.UUIDFkRelatedSourceModel.create(model=first)
    second_relation = await testmodels.UUIDFkRelatedSourceModel.create(model=second)

    result = await testmodels.UUIDFkRelatedSourceModel.filter(**{f"model__{lookup}": [first]})
    assert result == [first_relation if lookup == "in" else second_relation]


@pytest.mark.asyncio
@pytest.mark.parametrize("lookup", ["in", "not_in"])
async def test_membership_with_empty_values(db, lookup: str) -> None:
    tournament = await testmodels.Tournament.create(name="first")
    relation = await testmodels.MinRelation.create(tournament=tournament)

    result = await testmodels.MinRelation.filter(**{f"tournament__{lookup}": []})
    assert result == ([] if lookup == "in" else [relation])


@pytest.mark.asyncio
async def test_membership_with_subquery(db) -> None:
    first = await testmodels.Tournament.create(name="first")
    second = await testmodels.Tournament.create(name="second")
    relation = await testmodels.MinRelation.create(tournament=first)
    await testmodels.MinRelation.create(tournament=second)
    selected = Subquery(testmodels.Tournament.filter(name="first").values("id"))

    assert await testmodels.MinRelation.filter(tournament__in=selected) == [relation]


@pytest.mark.asyncio
async def test_existing_foreign_key_filters(db) -> None:
    first = await testmodels.Tournament.create(name="first")
    second = await testmodels.Tournament.create(name="second")
    relation = await testmodels.MinRelation.create(tournament=first)
    await testmodels.MinRelation.create(tournament=second)

    assert await testmodels.MinRelation.filter(tournament=first) == [relation]
    assert await testmodels.MinRelation.filter(tournament_id__in=[first.pk]) == [relation]
    assert await testmodels.MinRelation.filter(tournament__name__in=["first"]) == [relation]


@pytest.mark.asyncio
async def test_existing_annotation_filter_name(db) -> None:
    tournament = await testmodels.Tournament.create(name="first")
    relation = await testmodels.MinRelation.create(tournament=tournament)
    await testmodels.MinRelation.create(tournament=tournament)

    result = await (
        testmodels.MinRelation.annotate(tournament__in=F("id"))
        .filter(tournament__in=relation.pk)
        .values("id")
    )
    assert result == [{"id": relation.pk}]


@pytest.mark.asyncio
async def test_trailing_lookup_separator_still_raises(db) -> None:
    tournament = await testmodels.Tournament.create(name="first")
    await testmodels.MinRelation.create(tournament=tournament)

    with pytest.raises(FieldError, match="Unknown filter param"):
        await testmodels.MinRelation.filter(**{"tournament__": tournament})


@pytest.mark.asyncio
@pytest.mark.parametrize("lookup", ["in", "not_in"])
async def test_nullable_relation_membership(db, lookup: str) -> None:
    parent = await testmodels.UUIDPkSourceModel.create()
    linked = await testmodels.UUIDFkRelatedNullSourceModel.create(model=parent)
    unlinked = await testmodels.UUIDFkRelatedNullSourceModel.create(model=None)

    result = await testmodels.UUIDFkRelatedNullSourceModel.filter(**{f"model__{lookup}": [parent]})
    assert result == ([linked] if lookup == "in" else [unlinked])


@pytest.mark.asyncio
async def test_nested_forward_relation_membership(db) -> None:
    first = await testmodels.School.create(name="first", id=101)
    second = await testmodels.School.create(name="second", id=202)
    selected = await testmodels.Student.create(name="first", school=first)
    await testmodels.Student.create(name="second", school=second)
    await testmodels.Principal.create(name="first", school=first)
    await testmodels.Principal.create(name="second", school=second)

    assert await testmodels.Student.filter(school__principal__school__in=[first]) == [selected]
