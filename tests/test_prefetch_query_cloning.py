import pytest

from tests.testmodels import UUIDFkRelatedNullModel, UUIDPkModel
from tortoise.query_utils import Prefetch


@pytest.mark.asyncio
async def test_custom_prefetch_does_not_mutate_original_queryset(db):
    parent = await UUIDPkModel.create()
    child = await UUIDFkRelatedNullModel.create(name="example", model=parent)
    original = UUIDFkRelatedNullModel.filter(pk=child.pk).prefetch_related(
        Prefetch("model", UUIDPkModel.all(), to_attr="first_parent")
    )
    derived = original.prefetch_related(
        Prefetch("model", UUIDPkModel.all(), to_attr="second_parent")
    )
    original_child = await original.get()
    assert original_child.first_parent.pk == parent.pk
    assert not hasattr(original_child, "second_parent")
    derived_child = await derived.get()
    assert derived_child.first_parent.pk == parent.pk
    assert derived_child.second_parent.pk == parent.pk
