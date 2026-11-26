from uuid import uuid4

import pytest

from tests.testmodels import UUIDFkRelatedNullModel


@pytest.mark.asyncio
async def test_clone_regenerates_default_primary_key(db):
    original = await UUIDFkRelatedNullModel.create(name="example")
    cloned = original.clone()
    assert cloned.pk is not None
    assert cloned.pk != original.pk
    await cloned.save()
    assert await UUIDFkRelatedNullModel.filter(name="example").count() == 2
    assert (await UUIDFkRelatedNullModel.get(pk=original.pk)).name == "example"


@pytest.mark.asyncio
async def test_clone_awaits_async_primary_key_default(db, monkeypatch):
    original = await UUIDFkRelatedNullModel.create(name="example")
    expected = uuid4()

    async def default():
        return expected

    monkeypatch.setattr(UUIDFkRelatedNullModel._meta.pk, "default", default)
    cloned = original.clone()
    assert original._await_when_save == {}
    await cloned.save()
    assert cloned.pk == expected
    assert original._await_when_save == {}
    assert await UUIDFkRelatedNullModel.filter(name="example").count() == 2
