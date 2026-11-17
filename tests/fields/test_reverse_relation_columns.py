from collections.abc import Sequence

import pytest
import pytest_asyncio

from tests import testmodels
from tortoise.models import Model

ReverseCase = tuple[type[Model], str, Sequence[Model], Sequence[Model]]


@pytest_asyncio.fixture(params=["plain", "renamed", "renamed_join", "renamed_o2o", "o2o_pk"])
async def reverse_case(db, request: pytest.FixtureRequest) -> ReverseCase:
    parents: list[Model]
    children: list[Model]
    if request.param == "o2o_pk":
        tournament = await testmodels.Tournament.create(name="tournament")
        parents = [
            await testmodels.Event.create(name=str(i), tournament=tournament) for i in range(3)
        ]
        children = [
            await testmodels.Address.create(city=str(i), street="street", event=parent)
            for i, parent in enumerate(parents[:2])
        ]
        return testmodels.Event, "address", parents, children
    if request.param == "renamed_o2o":
        parents = [await testmodels.SourceFields.create(chars=f"parent{i}") for i in range(3)]
        children = [
            await testmodels.SourceFields.create(chars=f"child{i}", o2o=parent)
            for i, parent in enumerate(parents[:2])
        ]
        return testmodels.SourceFields, "o2o_rev", parents, children
    if request.param == "renamed_join":
        parents = [await testmodels.FKSourceFields.create() for _ in range(3)]
        children = [
            await testmodels.FKSourceFields.create(renamed=parent) for parent in parents[:2]
        ]
        return testmodels.FKSourceFields, "renamed_rev", parents, children
    parent_model, child_model = (
        (testmodels.UUIDPkSourceModel, testmodels.UUIDFkRelatedSourceModel)
        if request.param == "renamed"
        else (testmodels.UUIDPkModel, testmodels.UUIDFkRelatedModel)
    )
    parents = [await parent_model.create() for _ in range(3)]
    children = [await child_model.create(model=parent) for parent in parents[:2]]
    return parent_model, "children", parents, children


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("lookup", "selected"),
    [
        ("", [0]),
        ("__not", [1, 2]),
        ("__in", [0]),
        ("__not_in", [1, 2]),
        ("__isnull", [2]),
        ("__not_isnull", [0, 1]),
    ],
)
async def test_reverse_relation_columns(
    reverse_case: ReverseCase, lookup: str, selected: list[int]
) -> None:
    model, relation, parents, children = reverse_case
    value: object
    if lookup in ("__isnull", "__not_isnull"):
        value = True
    elif lookup in ("__in", "__not_in"):
        value = [children[0]]
    else:
        value = children[0].pk
    result = await model.filter(pk__in=[parent.pk for parent in parents]).filter(
        **{f"{relation}{lookup}": value}
    )
    assert {obj.pk for obj in result} == {parents[index].pk for index in selected}


@pytest.mark.asyncio
@pytest.mark.parametrize("lookup", ["__in", "__not_in"])
async def test_empty_reverse_membership(reverse_case: ReverseCase, lookup: str) -> None:
    model, relation, parents, _ = reverse_case
    result = await model.filter(pk__in=[parent.pk for parent in parents]).filter(
        **{f"{relation}{lookup}": []}
    )
    expected = parents if lookup == "__not_in" else []
    assert {obj.pk for obj in result} == {obj.pk for obj in expected}
