import pytest

from tests.testmodels import UUIDFkRelatedNullModel, UUIDPkModel
from tortoise.query_utils import Prefetch


@pytest.mark.asyncio
@pytest.mark.parametrize("relation", ["model", "parent"])
async def test_null_relation_sets_custom_prefetch_attribute(db, relation):
    child = await UUIDFkRelatedNullModel.create(name="example")
    fetched = (
        await UUIDFkRelatedNullModel.filter(pk=child.pk)
        .prefetch_related(Prefetch(relation, UUIDPkModel.all(), to_attr="cached_parent"))
        .get()
    )
    assert fetched.cached_parent is None
