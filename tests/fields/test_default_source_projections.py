import pytest
import pytest_asyncio

from tests import testmodels
from tortoise.expressions import F
from tortoise.models import Model


@pytest.fixture(params=[testmodels.StraightFields, testmodels.SourceFields])
def model(request: pytest.FixtureRequest) -> type[Model]:
    return request.param


@pytest_asyncio.fixture
async def record(db, model: type[Model]) -> tuple[Model, Model]:
    parent = await model.create(chars="parent")
    child = await model.create(chars="child", nullable="value", fk=parent)
    return parent, child


@pytest.mark.asyncio
@pytest.mark.parametrize("fetched", [False, True])
async def test_model_dictionary(
    model: type[Model], record: tuple[Model, Model], fetched: bool
) -> None:
    parent, child = record
    if fetched:
        child = await model.get(eyedee=child.pk)
    assert dict(child) == {
        "eyedee": child.pk,
        "chars": "child",
        "blip": "BLIP",
        "nullable": "value",
        "fk_id": parent.pk,
        "o2o_id": None,
    }


@pytest.mark.asyncio
async def test_unsaved_model_dictionary(db, model: type[Model]) -> None:
    assert dict(model(chars="draft")) == {
        "eyedee": None,
        "chars": "draft",
        "blip": "BLIP",
        "nullable": None,
        "fk_id": None,
        "o2o_id": None,
    }


@pytest.mark.asyncio
async def test_default_tuple_fields(model: type[Model], record: tuple[Model, Model]) -> None:
    parent, child = record
    assert await model.all().order_by("eyedee").values_list() == [
        (parent.pk, "parent", "BLIP", None, None, None),
        (child.pk, "child", "BLIP", "value", parent.pk, None),
    ]


@pytest.mark.asyncio
async def test_default_tuple_fields_with_annotation(
    model: type[Model], record: tuple[Model, Model]
) -> None:
    parent, child = record
    result = await model.filter(eyedee=child.pk).annotate(adjusted=F("eyedee") + 1).values_list()
    assert result == [(child.pk, "child", "BLIP", "value", parent.pk, None, child.pk + 1)]


@pytest.mark.asyncio
async def test_single_default_tuple(model: type[Model], record: tuple[Model, Model]) -> None:
    parent, child = record
    assert await model.get(eyedee=child.pk).values_list() == (
        child.pk,
        "child",
        "BLIP",
        "value",
        parent.pk,
        None,
    )


@pytest.mark.asyncio
async def test_explicit_tuple_fields(model: type[Model], record: tuple[Model, Model]) -> None:
    parent, child = record
    assert await model.filter(eyedee=child.pk).values_list("chars", "fk_id", "eyedee") == [
        ("child", parent.pk, child.pk)
    ]


@pytest.mark.asyncio
async def test_renamed_column_matching_virtual_relation(db) -> None:
    parent = await testmodels.FKSourceFields.create()
    child = await testmodels.FKSourceFields.create(same=parent)
    assert dict(child) == {
        "id": child.pk,
        "plain_id": None,
        "renamed_id": None,
        "same_id": parent.pk,
        "o2o_id": None,
    }
    assert await testmodels.FKSourceFields.filter(id=child.pk).values_list() == [
        (child.pk, None, None, parent.pk, None)
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("renamed", [False, True])
async def test_uuid_values_keep_python_types(db, renamed: bool) -> None:
    parent_model, child_model = (
        (testmodels.UUIDPkSourceModel, testmodels.UUIDFkRelatedSourceModel)
        if renamed
        else (testmodels.UUIDPkModel, testmodels.UUIDFkRelatedModel)
    )
    parent = await parent_model.create()
    child = await child_model.create(model=parent, name="child")
    assert dict(child) == {"id": child.pk, "name": "child", "model_id": parent.pk}
    assert await child_model.all().values_list() == [(child.pk, "child", parent.pk)]
